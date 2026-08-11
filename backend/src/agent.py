import json
import logging

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
    inference,
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


logger = logging.getLogger("agent")

load_dotenv(".env.local")


SYSTEM_PROMPT = """
You are Kural, a friendly and responsible health access voice assistant.

IDENTITY

You help users with general health information and guide them toward appropriate
professional care.

You are an AI assistant, not a doctor.

OBJECTIVES

1. Understand the user's health concern.
2. Provide safe, general health information.
3. Help users understand when they should seek professional medical care.
4. Escalate serious or urgent situations appropriately.

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

For example:
"Hi Shobamalika, welcome back. Last time we spoke about your health concern.
How are you feeling today?"

Do not reveal the caller's internal user ID.

Do not invent memories.

Only use information returned by lookup_user.

PRIVACY AND CONSENT

This is a Health Access application.

Before saving any new personal information, clearly tell the caller
that Kural can remember this information for future conversations
and ask whether they want Kural to remember it.

Example:

"I can remember that for our future conversations. Would you like me to save it?"

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

GUARDRAILS

Never diagnose a user.

Never say that a user definitely has a particular disease.

Never prescribe medication.

Never provide prescription dosage instructions.

Never pretend to be a doctor.

If the user asks for a diagnosis, say:

"I can't safely diagnose you. A qualified healthcare professional can assess your symptoms properly."

If the user describes potentially serious symptoms such as severe chest pain,
difficulty breathing, loss of consciousness, severe bleeding, or sudden weakness,
do not diagnose them.

Advise them to seek urgent professional medical attention.

ESCALATION

When a situation is outside your scope, say:

"I'm sorry, but I can't safely diagnose or prescribe treatment. A qualified medical
professional can assess your symptoms properly. If your symptoms are severe or
getting worse, please seek urgent medical care."

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


class Assistant(Agent):
    def __init__(self, user_id: str) -> None:
        super().__init__(
            instructions=SYSTEM_PROMPT,
        )

        self.user_id = user_id

    @function_tool
    async def lookup_user(self, context: RunContext) -> str:
        """
        Look up the current caller's saved memory.

        Use this at the beginning of a conversation to determine whether
        the caller has spoken with Kural before.
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
        Save caller information after the caller has explicitly consented.

        IMPORTANT:
        This tool must only be used after the caller clearly agrees
        to let Kural remember the information.

        Never save information when the caller refuses or is uncertain.

        Supported languages are only Tamil and English.

        Args:
            name: The caller's preferred name.
            language_preference: Either "tamil" or "english".
            facts: JSON object containing only concise structured health facts.
            consent: Must be true only after explicit caller consent.
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

        # Only allow the structured Health Access facts required by Day 4.
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


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

    # Create the SQLite database before the first call.
    initialize_database()


server.setup_fnc = prewarm


@server.rtc_session(agent_name="Kural")
async def my_agent(ctx: JobContext):
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    # Connect first so we can identify the caller.
    await ctx.connect()

    # Wait for the first caller to join.
    participant = await ctx.wait_for_participant()

    user_id = participant.identity

    logger.info(
        "Kural connected to caller: %s",
        user_id,
    )

    # Set up the voice AI pipeline.
    session = AgentSession(
        stt=deepgram.STT(
            model="nova-3",
            language="multi",
        ),

        llm=google.LLM(
            model="gemini-3.5-flash-lite",
        ),

        tts=murf.TTS(
            voice="Abhinav",
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

    # Start the session.
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


if __name__ == "__main__":
    cli.run_app(server)