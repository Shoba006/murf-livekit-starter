import json
import logging
from datetime import datetime, timezone

from dotenv import load_dotenv
from livekit import rtc

from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    RunContext,
    cli,
    function_tool,
    tokenize,
    room_io,
)

from livekit.plugins import (
    murf,
    silero,
    google,
    deepgram,
    noise_cancellation,
)

from livekit.plugins.turn_detector.multilingual import MultilingualModel

from memory import (
    initialize_database,
    lookup_user as db_lookup_user,
    save_user_memory as db_save_user_memory,
)

from healthcare import find_healthcare_facilities

from escalation import (
    initialize_escalation_database,
    create_escalation as db_create_escalation,
)

from analytics import (
    initialize_analytics_database,
    record_call,
)


logger = logging.getLogger("agent")

load_dotenv(".env.local")


# ============================================================
# MAIN KURAL PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are Kural, a friendly and responsible health access voice assistant.

IDENTITY

You help users with general health information and guide them toward
appropriate professional care.

You are an AI assistant, not a doctor.

OBJECTIVES

1. Understand the user's health concern.
2. Provide safe, general health information.
3. Help users understand when they should seek professional medical care.
4. Escalate serious or urgent situations appropriately.
5. Help users find nearby healthcare facilities.
6. Know when a human healthcare professional should take over.
7. Hand off clinic and appointment-related requests to the Clinic and
   Appointment Specialist.

KNOWLEDGE

You can provide general educational information about common health topics,
symptoms, healthy habits, and basic healthcare guidance.

Do not diagnose diseases or medical conditions.

Do not prescribe prescription medicines or give prescription dosages.

Never claim certainty about a user's medical condition.

LANGUAGE

Kural supports ONLY Tamil and English.

If the user speaks English, respond in English.

If the user speaks Tamil, respond in proper Tamil script.

If the user speaks Tamil mixed with English, respond naturally in Tamil-English.

If the user changes between Tamil and English, follow their current language.

Do not use Hindi, Telugu, Bengali, Malayalam, Kannada, Marathi,
or any other language.

Never romanize Tamil.

When speaking Tamil, use Tamil script.

STYLE

Be warm, calm, empathetic, and concise.

Use short sentences that sound natural when spoken.

Ask one question at a time.

Do not use complex formatting, emojis, or symbols.

MEMORY

Kural has a persistent memory system.

At the beginning of every conversation, use the lookup_user tool
to check whether this caller has been seen before.

If the caller is returning and saved memory exists, greet them by name
and naturally use relevant saved information.

Do not reveal the caller's internal user ID.

Do not invent memories.

Only use information returned by lookup_user.

PRIVACY AND CONSENT

This is a Health Access application.

Before saving any new personal information, clearly tell the caller
that Kural can remember this information for future conversations
and ask whether they want Kural to remember it.

Only call save_user_memory after the caller clearly agrees.

If the caller says no, do not save the information.

If the caller is uncertain, asks what will be saved, or does not clearly agree,
do not save anything.

Never save written-out medical notes.

For Health Access memory, only save concise structured facts such as:

- age_band
- ongoing_condition
- last_triage_outcome

Do not store unnecessary medical details.

HEALTHCARE FACILITY LOOKUP

Kural has a healthcare facility lookup tool called
find_healthcare_facility.

Use this tool when the caller asks to find a nearby:

- hospital
- clinic
- healthcare facility
- doctor facility
- PHC
- primary health centre
- similar healthcare facility

If the caller asks for a nearby healthcare facility but has not provided
a city, town, district, or locality, ask them for their location.

Do not invent a healthcare facility.

Do not claim that a facility is open, available, accepting patients,
or currently providing a particular service unless the tool explicitly
provides that information.

Do not read raw JSON or technical tool output to the caller.

Convert tool results into a natural spoken response.

If the tool fails, tell the caller that the facility lookup is temporarily
unavailable and that you cannot reliably provide a current result.

Do not guess a facility when the tool fails.

If the tool returns no facilities, explain that no matching facilities
were found within the search area.

SPECIALIST HANDOFF

Kural has a separate Clinic and Appointment Specialist.

The specialist handles:

- clinic selection
- choosing between healthcare facility options
- preparing for a clinic visit
- appointment-related questions
- what information the user may need before contacting a clinic
- general appointment preparation

If the caller clearly asks for clinic or appointment assistance,
handoff to the Clinic and Appointment Specialist.

Examples:

"I want to book an appointment."

"Which clinic should I visit?"

"Help me choose a clinic."

"I need to prepare for my doctor's appointment."

"Can you help me with an appointment?"

Before handing off, tell the caller clearly:

"I'll connect you to our clinic and appointment specialist."

Then use the transfer_to_clinic_specialist tool.

Do NOT hand off ordinary health questions.

Do NOT hand off emergency or red-flag situations to the specialist.
Handle those using the escalation process.

The specialist receives the existing conversation context, so do not ask
the caller to repeat everything.

HUMAN HELP / ESCALATION

Kural must ask for human help in these two situations:

1. The caller describes a potentially serious or red-flag symptom.
2. The caller asks Kural to diagnose a medical condition.

For serious symptoms such as severe chest pain, difficulty breathing,
loss of consciousness, severe bleeding, sudden weakness, or other
potentially dangerous symptoms:

- Do not diagnose the caller.
- Tell them that the situation may require urgent professional attention.
- Explain that Kural can create a human-help request.
- Before sharing information with a human, ask for the caller's permission.
- Only call create_escalation after the caller clearly gives permission.
- If the caller refuses, do not create the request.
- If the situation appears immediately life-threatening, strongly advise
  seeking emergency medical care immediately.

For diagnosis requests:

- Explain that Kural cannot safely diagnose them.
- Offer to create a human-help request so a qualified professional can
  review the situation.
- Ask for permission before sharing information.
- Only create the request after explicit consent.

When asking for escalation permission, clearly explain what will be shared.

For example:

"I can create a request for a healthcare professional. I would share a
short summary of what you told me, what I checked, the urgency, and your
preferred language. Would you like me to send that request?"

Never send the full conversation.

Never include passwords, OTPs, PINs, account numbers, or unnecessary
private information.

After create_escalation succeeds:

- Give the caller the reference ID.
- Tell them the request is open.
- Explain that a human professional can review the request.
- Do not promise an immediate response unless that is actually guaranteed.

If escalation creation fails:

- Tell the caller that the request could not be created.
- Do not invent a reference ID.
- Still advise them to seek appropriate professional care.

GUARDRAILS

Never diagnose a user.

Never say that a user definitely has a particular disease.

Never prescribe medication.

Never provide prescription dosage instructions.

Never pretend to be a doctor.

If the user asks for a diagnosis, say:

"I can't safely diagnose you. A qualified healthcare professional can assess
your symptoms properly."

If the user describes potentially serious symptoms such as severe chest pain,
difficulty breathing, loss of consciousness, severe bleeding, or sudden weakness,
do not diagnose them.

Advise them to seek urgent professional medical attention.

OUT OF SCOPE

If the user asks about something unrelated to healthcare, politely explain
that your role is limited to health information and guidance.

GREETING

For a new caller, start with:

"Hi, I'm Kural. I'm a health access assistant. I can help with general health
information and guide you on when to seek professional care. How can I help you today?"

For a returning caller, greet them by their saved name and use relevant
saved information naturally.
"""


# ============================================================
# CLINIC + APPOINTMENT SPECIALIST
# ============================================================

SPECIALIST_PROMPT = """
You are Kural's Clinic and Appointment Specialist.

You are a focused healthcare access specialist.

YOUR JOB

Help users with:

- choosing a suitable clinic or healthcare facility
- understanding which type of facility may be appropriate
- preparing for a clinic visit
- appointment-related questions
- what information they may need when contacting a clinic
- finding nearby healthcare facilities

You are NOT a doctor.

You do NOT diagnose medical conditions.

You do NOT prescribe medication.

You do NOT provide prescription dosages.

You do NOT claim that a clinic has appointment availability unless
real availability information is provided by a tool.

LANGUAGE

You support ONLY Tamil and English.

If the user speaks English, respond in English.

If the user speaks Tamil, respond in proper Tamil script.

If the user speaks Tamil-English, respond naturally in Tamil-English.

Never use Hindi, Telugu, Bengali, Malayalam, Kannada, Marathi,
or any other language.

Never romanize Tamil.

STYLE

Be warm, concise, and practical.

Ask one question at a time.

The user has already spoken with Kural.

Do not ask the user to repeat the entire problem.

Use the conversation history provided by Kural.

HANDOFF CONTEXT

Kural has transferred the conversation to you because the user needs
clinic or appointment-related assistance.

Briefly introduce yourself.

For example:

"Hi, I'm Kural's clinic and appointment specialist. I can help you
with choosing a clinic or preparing for an appointment."

Then continue directly with the user's request.

HEALTHCARE FACILITY LOOKUP

You can use the healthcare facility lookup tool.

Use it when the user asks for nearby:

- hospitals
- clinics
- PHCs
- primary health centres
- healthcare facilities

If location is missing, ask for the city, town, district, or locality.

Do not invent facilities.

Do not claim that a facility is open or has appointment availability
unless the tool explicitly provides that information.

APPOINTMENTS

You cannot actually book an appointment unless a real booking tool is
provided.

If the user asks to book an appointment, help them prepare by asking
for relevant information such as:

- preferred clinic
- preferred date
- preferred time
- type of healthcare professional

Do not claim that an appointment has been booked.

If the user needs urgent medical attention, stop appointment planning
and advise them to seek urgent professional care.

OUT OF SCOPE

If the user changes to a general health question, you may answer basic
health access questions.

If they need diagnosis or serious medical assessment, tell them that
a qualified healthcare professional should assess them.

Do not diagnose.
"""


# ============================================================
# MAIN AGENT
# ============================================================

class Assistant(Agent):

    def __init__(self, user_id: str) -> None:
        super().__init__(
            instructions=SYSTEM_PROMPT,
        )

        self.user_id = user_id

    # --------------------------------------------------------
    # MEMORY
    # --------------------------------------------------------

    @function_tool
    async def lookup_user(
        self,
        context: RunContext,
    ) -> str:
        """
        Look up the current caller's saved memory.

        Use this at the beginning of a conversation.
        """

        logger.info(
            "Looking up Kural memory for user_id=%s",
            self.user_id,
        )

        result = db_lookup_user(self.user_id)

        if not result["found"]:
            return json.dumps(
                {
                    "found": False,
                    "message": "No saved memory exists for this caller.",
                },
                ensure_ascii=False,
            )

        return json.dumps(
            {
                "found": True,
                "name": result["name"],
                "language_preference": result["language_preference"],
                "facts": result["facts"],
                "last_interaction": result["last_interaction"],
            },
            ensure_ascii=False,
        )

    @function_tool
    async def save_user_memory(
        self,
        context: RunContext,
        name: str | None = None,
        language_preference: str | None = None,
        facts: str | None = None,
        consent: bool = False,
    ) -> str:
        """
        Save caller information after explicit consent.

        Consent must be true only after the caller clearly agrees.
        """

        if not consent:
            logger.warning(
                "Memory save blocked because consent was not provided "
                "for user_id=%s",
                self.user_id,
            )

            return (
                "Memory was NOT saved because the caller did not explicitly "
                "give consent."
            )

        if language_preference not in (None, "tamil", "english"):
            return (
                "Memory was not saved because the language preference "
                "must be tamil or english."
            )

        parsed_facts: dict = {}

        if facts:
            try:
                parsed_facts = json.loads(facts)

                if not isinstance(parsed_facts, dict):
                    parsed_facts = {}

            except json.JSONDecodeError:
                logger.warning(
                    "Invalid facts JSON received for user_id=%s",
                    self.user_id,
                )

                return "Memory was not saved because the facts were invalid."

        allowed_fact_keys = {
            "age_band",
            "ongoing_condition",
            "last_triage_outcome",
        }

        parsed_facts = {
            key: value
            for key, value in parsed_facts.items()
            if key in allowed_fact_keys
        }

        result = db_save_user_memory(
            user_id=self.user_id,
            name=name,
            language_preference=language_preference,
            facts=parsed_facts,
        )

        logger.info(
            "Saved Kural memory for user_id=%s",
            self.user_id,
        )

        return json.dumps(
            {
                "success": True,
                "message": "Caller memory saved successfully.",
                "name": result["name"],
                "language_preference": result["language_preference"],
                "facts": result["facts"],
            },
            ensure_ascii=False,
        )

    # --------------------------------------------------------
    # HEALTHCARE LOOKUP
    # --------------------------------------------------------

    @function_tool
    async def find_healthcare_facility(
        self,
        context: RunContext,
        location: str,
        facility_type: str = "any",
    ) -> str:
        """
        Find nearby healthcare facilities using real OpenStreetMap data.

        Use this for hospitals, clinics, PHCs and healthcare facilities.
        """

        logger.info(
            "Healthcare facility lookup requested: "
            "location=%s, facility_type=%s, user_id=%s",
            location,
            facility_type,
            self.user_id,
        )

        try:
            result = find_healthcare_facilities(
                location=location,
                facility_type=facility_type,
                limit=3,
            )

        except Exception:
            logger.exception(
                "Unexpected healthcare lookup failure for location=%s",
                location,
            )

            return json.dumps(
                {
                    "success": False,
                    "error": (
                        "The healthcare facility lookup failed unexpectedly. "
                        "Do not invent a facility."
                    ),
                },
                ensure_ascii=False,
            )

        return json.dumps(
            result,
            ensure_ascii=False,
        )

    # --------------------------------------------------------
    # DAY 9 HANDOFF
    # --------------------------------------------------------

    @function_tool
    async def transfer_to_clinic_specialist(
        self,
        context: RunContext,
    ):
        """
        Transfer the caller to the Clinic and Appointment Specialist.

        Use this ONLY when the caller needs focused help with:
        - choosing a clinic
        - clinic selection
        - appointment questions
        - preparing for an appointment
        - finding a suitable healthcare facility

        Do NOT use this for ordinary health questions.

        Do NOT use this for emergency or red-flag symptoms.

        The specialist receives the existing conversation context, so
        the caller does not need to repeat their problem.
        """

        logger.info(
            "Handing off caller %s to Clinic and Appointment Specialist",
            self.user_id,
        )

        specialist = ClinicAppointmentSpecialist(
            user_id=self.user_id,
            chat_ctx=self.chat_ctx,
        )

        return (
            specialist,
            "I'm connecting you to our clinic and appointment specialist.",
        )

    # --------------------------------------------------------
    # ESCALATION
    # --------------------------------------------------------

    @function_tool
    async def create_escalation(
        self,
        context: RunContext,
        issue_type: str,
        summary: str,
        what_happened: str,
        agent_checked: str = "",
        urgency: str = "high",
        language: str = "",
        follow_up_method: str = "",
        consent: bool = False,
    ) -> str:
        """
        Create a human-help request after explicit caller consent.
        """

        if not consent:
            logger.warning(
                "Escalation blocked because caller did not consent. "
                "user_id=%s",
                self.user_id,
            )

            return json.dumps(
                {
                    "success": False,
                    "message": (
                        "The caller did not explicitly consent. "
                        "No human-help request was created."
                    ),
                },
                ensure_ascii=False,
            )

        if not issue_type.strip():
            return json.dumps(
                {
                    "success": False,
                    "message": "Issue type is required.",
                },
                ensure_ascii=False,
            )

        if not summary.strip():
            return json.dumps(
                {
                    "success": False,
                    "message": "A short summary is required.",
                },
                ensure_ascii=False,
            )

        if not what_happened.strip():
            return json.dumps(
                {
                    "success": False,
                    "message": "A description of what happened is required.",
                },
                ensure_ascii=False,
            )

        try:
            result = db_create_escalation(
                user_id=self.user_id,
                issue_type=issue_type.strip(),
                summary=summary.strip(),
                what_happened=what_happened.strip(),
                agent_checked=agent_checked.strip(),
                urgency=urgency.strip().lower(),
                language=language.strip(),
                follow_up_method=follow_up_method.strip(),
            )

        except Exception:
            logger.exception(
                "Failed to create escalation for user_id=%s",
                self.user_id,
            )

            return json.dumps(
                {
                    "success": False,
                    "message": (
                        "The human-help request could not be created. "
                        "Do not invent a reference ID."
                    ),
                },
                ensure_ascii=False,
            )

        logger.info(
            "Created escalation reference_id=%s for user_id=%s",
            result["reference_id"],
            self.user_id,
        )

        return json.dumps(
            {
                "success": True,
                "reference_id": result["reference_id"],
                "status": result["status"],
                "urgency": result["urgency"],
                "created_at": result["created_at"],
                "message": "Human-help request created successfully.",
            },
            ensure_ascii=False,
        )


# ============================================================
# CLINIC + APPOINTMENT SPECIALIST
# ============================================================

class ClinicAppointmentSpecialist(Agent):

    def __init__(
        self,
        user_id: str,
        chat_ctx=None,
    ) -> None:

        super().__init__(
            instructions=SPECIALIST_PROMPT,
            chat_ctx=chat_ctx,
        )

        self.user_id = user_id

    async def on_enter(self) -> None:
        """
        Introduce the specialist after the handoff.

        The previous conversation is already available through chat_ctx.
        """

        logger.info(
            "Clinic and Appointment Specialist took over for user_id=%s",
            self.user_id,
        )

        await self.session.generate_reply(
            instructions=(
                "Introduce yourself briefly as Kural's clinic and "
                "appointment specialist. Continue directly from the "
                "caller's previous request. Do not ask them to repeat "
                "their entire problem."
            )
        )

    @function_tool
    async def find_healthcare_facility(
        self,
        context: RunContext,
        location: str,
        facility_type: str = "any",
    ) -> str:
        """
        Find nearby healthcare facilities using real OpenStreetMap data.

        Use this when the caller needs help finding a clinic, hospital,
        PHC or healthcare facility.
        """

        logger.info(
            "Specialist healthcare lookup: location=%s, type=%s, user_id=%s",
            location,
            facility_type,
            self.user_id,
        )

        try:
            result = find_healthcare_facilities(
                location=location,
                facility_type=facility_type,
                limit=3,
            )

        except Exception:
            logger.exception(
                "Specialist healthcare lookup failed for location=%s",
                location,
            )

            return json.dumps(
                {
                    "success": False,
                    "error": (
                        "The healthcare facility lookup is temporarily "
                        "unavailable."
                    ),
                },
                ensure_ascii=False,
            )

        return json.dumps(
            result,
            ensure_ascii=False,
        )


# ============================================================
# LIVEKIT SERVER
# ============================================================

server = AgentServer()


# ============================================================
# PREWARM
# ============================================================

def prewarm(proc: JobProcess):

    proc.userdata["vad"] = silero.VAD.load()

    initialize_database()
    initialize_escalation_database()
    initialize_analytics_database()


server.setup_fnc = prewarm


# ============================================================
# LIVEKIT SESSION
# ============================================================

@server.rtc_session(agent_name="Kural")
async def my_agent(ctx: JobContext):

    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    # Connect to LiveKit.
    await ctx.connect()

    # Wait for caller.
    participant = await ctx.wait_for_participant()

    user_id = participant.identity

    call_id = ctx.room.name
    call_started_at = datetime.now(timezone.utc).isoformat()

    logger.info(
        "Kural connected to caller: %s",
        user_id,
    )

    # --------------------------------------------------------
    # SESSION
    # --------------------------------------------------------

    session = AgentSession(

        # Tamil speech recognition
        stt=deepgram.STT(
            model="nova-3",
            language="ta",
        ),

        # Gemini
        llm=google.LLM(
            model="gemini-3.5-flash-lite",
        ),

        # Murf Falcon / Anisha
        tts=murf.TTS(
            voice="Anisha",
            style="Conversation",
            tokenizer=tokenize.basic.SentenceTokenizer(
                min_sentence_len=2
            ),
            text_pacing=True,
        ),

        turn_detection=MultilingualModel(),

        vad=ctx.proc.userdata["vad"],

        preemptive_generation=True,
    )

    try:

        # ----------------------------------------------------
        # START SESSION
        # ----------------------------------------------------

        await session.start(
            agent=Assistant(user_id=user_id),
            room=ctx.room,
            room_options=room_io.RoomOptions(
                audio_input=room_io.AudioInputOptions(
                    noise_cancellation=lambda params: (
                        noise_cancellation.BVCTelephony()
                        if params.participant.kind
                        == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
                        else noise_cancellation.BVC()
                    ),
                ),
            ),
        )

        logger.info(
            "Kural session started successfully: %s",
            call_id,
        )

        # IMPORTANT:
        # Do NOT call session.wait_for_disconnect().
        #
        # AgentSession in the installed LiveKit Agents version does not
        # provide that method. The LiveKit session lifecycle is managed
        # by the framework after session.start().

    except Exception:

        logger.exception(
            "Kural session failed: %s",
            call_id,
        )

        # Analytics must never crash the voice agent.
        try:

            record_call(
                call_id=call_id,
                user_id=user_id,
                outcome="failed",
                success_reason="Call ended unexpectedly",
                channel="browser",
                started_at=call_started_at,
                ended_at=datetime.now(timezone.utc).isoformat(),
            )

        except Exception:

            logger.exception(
                "Failed to record analytics for call=%s",
                call_id,
            )

        raise


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    cli.run_app(server)