import json
import math
from datetime import date, datetime

import streamlit as st
from strands import Agent, tool

# ---------------------------------------------------------------------------
# Load course data
# ---------------------------------------------------------------------------

with open("courses.json", "r") as f:
    courses: dict = json.load(f)

# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------


@tool
def get_course_info(course_code: str) -> str:
    """Get course name, exam date, credits, and description for a course code."""
    code = course_code.upper()
    if code not in courses:
        return f"Course '{code}' not found. Available courses: {', '.join(courses.keys())}"

    c = courses[code]
    return (
        f"Course: {c['name']} ({code})\n"
        f"Credits: {c['credits']}\n"
        f"Exam Date: {c['exam_date']}\n"
        f"Description: {c['description']}\n"
        f"Key Topics: {', '.join(c['key_topics'])}"
    )


@tool
def calculate_study_plan(course_code: str, free_hours_per_day: float) -> str:
    """Generate a daily study schedule based on days until the exam and free hours available per day."""
    code = course_code.upper()
    if code not in courses:
        return f"Course '{code}' not found. Available courses: {', '.join(courses.keys())}"

    c = courses[code]
    exam = datetime.strptime(c["exam_date"], "%Y-%m-%d").date()
    today = date.today()
    days_remaining = (exam - today).days

    if days_remaining <= 0:
        return f"The exam for {code} has already passed or is today!"

    topics = c["key_topics"]
    num_topics = len(topics)

    # Divide days evenly across topics, reserving the last day for review
    review_days = max(1, days_remaining // 5)
    study_days = days_remaining - review_days
    days_per_topic = max(1, study_days // num_topics)

    # Build the plan
    lines = [
        f"Study Plan for {c['name']} ({code})",
        f"Exam date: {c['exam_date']} ({days_remaining} days remaining)",
        f"Available: {free_hours_per_day} hours/day",
        "",
        "--- Daily Schedule ---",
    ]

    # Session breakdown per day
    sessions_per_day = max(1, int(free_hours_per_day // 1.5))
    session_length = round(free_hours_per_day / sessions_per_day, 1)
    break_minutes = 10 if session_length <= 1.5 else 15

    lines.append(
        f"Sessions per day: {sessions_per_day} x {session_length}h "
        f"(with {break_minutes}-min breaks between sessions)"
    )
    lines.append("")
    lines.append("--- Topic Schedule ---")

    current_day = 1
    for i, topic in enumerate(topics):
        start_day = current_day
        end_day = current_day + days_per_topic - 1
        lines.append(f"Days {start_day}-{end_day}: {topic}")
        current_day = end_day + 1

    lines.append(f"Days {current_day}-{days_remaining}: Review & Practice Exams")
    lines.append("")
    lines.append("Tips: Start each session with a 5-min recap of the previous day. "
                 "End each day with a self-quiz on what you covered.")

    return "\n".join(lines)


@tool
def get_study_tips(subject: str) -> str:
    """Return proven study techniques for a subject area, e.g., math, programming, theory."""
    tips_db = {
        "math": (
            "Math Study Tips:\n"
            "1. Practice problems daily - repetition builds fluency.\n"
            "2. Understand derivations, don't just memorize formulas.\n"
            "3. Work through examples step-by-step before attempting exercises.\n"
            "4. Use spaced repetition for key theorems and identities.\n"
            "5. Teach concepts to someone else to find gaps in understanding."
        ),
        "programming": (
            "Programming Study Tips:\n"
            "1. Write code every day - even 20 minutes helps.\n"
            "2. Build small projects to apply concepts practically.\n"
            "3. Read and trace through existing code to understand patterns.\n"
            "4. Use debugging as a learning tool - step through execution.\n"
            "5. Explain your code out loud (rubber-duck debugging)."
        ),
        "theory": (
            "Theory Study Tips:\n"
            "1. Create concept maps linking ideas together.\n"
            "2. Use active recall - close the book and write what you remember.\n"
            "3. Summarize each chapter in your own words.\n"
            "4. Form study groups to discuss and debate concepts.\n"
            "5. Use the Feynman technique: explain it simply, find gaps, refine."
        ),
        "science": (
            "Science Study Tips:\n"
            "1. Connect theory to real-world examples and experiments.\n"
            "2. Draw diagrams and label processes step by step.\n"
            "3. Practice unit conversions and dimensional analysis.\n"
            "4. Review lab work and relate observations to theory.\n"
            "5. Use flashcards for key terms, constants, and equations."
        ),
        "writing": (
            "Writing Study Tips:\n"
            "1. Read high-quality examples in your discipline.\n"
            "2. Outline before you draft - structure saves time.\n"
            "3. Write first, edit later - don't self-censor in the first pass.\n"
            "4. Get peer feedback early and often.\n"
            "5. Practice timed writing to prepare for exam conditions."
        ),
    }

    key = subject.lower().strip()
    # Try to match partial keys
    for k, v in tips_db.items():
        if k in key or key in k:
            return v

    available = ", ".join(tips_db.keys())
    return (
        f"No specific tips found for '{subject}'. "
        f"Available subjects: {available}. "
        "General tip: Use active recall, spaced repetition, and practice problems."
    )


@tool
def web_search(query: str) -> str:
    """Search the internet for information on any topic. Use this when students ask about topics not covered by the local course data, or when they need up-to-date information, explanations, or external resources."""
    try:
        from duckduckgo_search import DDGS

        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=5):
                results.append(
                    f"**{r['title']}**\n{r['body']}\nLink: {r['href']}"
                )

        if results:
            return f"Search results for '{query}':\n\n" + "\n\n---\n\n".join(results)
        else:
            return f"No results found for '{query}'. Try rephrasing your search."

    except Exception as e:
        return f"Search failed: {str(e)}. Please try again or rephrase your query."


@tool
def send_email(recipient_email: str, subject: str, body: str) -> str:
    """Send an email with study plan or schedule content to the specified email address. Use this when a student asks to email or send their study plan, schedule, or any content to their email."""
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    # Get SMTP config from session state
    smtp_email = st.session_state.get("smtp_email", "")
    smtp_password = st.session_state.get("smtp_password", "")
    smtp_provider = st.session_state.get("smtp_provider", "Gmail")

    if not smtp_email or not smtp_password:
        return (
            "Email not configured! Please set up your email in the sidebar first:\n"
            "1. Enter your email address\n"
            "2. Enter your app password (not your regular password)\n"
            "3. Select your email provider\n"
            "Then try again."
        )

    # SMTP server settings
    smtp_configs = {
        "Gmail": ("smtp.gmail.com", 587),
        "QQ Mail": ("smtp.qq.com", 587),
        "163 Mail": ("smtp.163.com", 587),
        "Outlook": ("smtp-mail.outlook.com", 587),
    }

    server_host, server_port = smtp_configs.get(smtp_provider, ("smtp.gmail.com", 587))

    try:
        # Create email
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"📚 StudyBuddy: {subject}"
        msg["From"] = smtp_email
        msg["To"] = recipient_email

        # Plain text version
        text_part = MIMEText(body, "plain", "utf-8")

        # HTML version
        html_body = (
            "<html><body>"
            "<h2>📚 StudyBuddy - Your Study Plan</h2>"
            "<pre style='font-family: Arial, sans-serif; font-size: 14px; line-height: 1.8;'>"
            + body.replace("\n", "<br>")
            + "</pre>"
            "<hr><p style='color: #666; font-size: 12px;'>Sent by StudyBuddy - Your personal learning planner</p>"
            "</body></html>"
        )
        html_part = MIMEText(html_body, "html", "utf-8")

        msg.attach(text_part)
        msg.attach(html_part)

        # Send
        with smtplib.SMTP(server_host, server_port) as server:
            server.starttls()
            server.login(smtp_email, smtp_password)
            server.sendmail(smtp_email, recipient_email, msg.as_string())

        return f"Email sent successfully to {recipient_email}! ✅"

    except smtplib.SMTPAuthenticationError:
        return (
            f"Authentication failed for {smtp_email}. Please check:\n"
            "- For Gmail: use an App Password (Settings > Security > App Passwords)\n"
            "- For QQ: use the authorization code (授权码) from QQ Mail settings\n"
            "- For 163: use the authorization code from 163 Mail settings"
        )
    except Exception as e:
        return f"Failed to send email: {str(e)}"


# ---------------------------------------------------------------------------
# Streamlit App
# ---------------------------------------------------------------------------

st.set_page_config(page_title="StudyBuddy", page_icon="📚", layout="centered")

# Sidebar
with st.sidebar:
    st.title("StudyBuddy")
    st.markdown("*Your personal learning planner*")
    st.divider()

    # Email configuration
    st.markdown("**📧 Email Settings**")
    smtp_email = st.text_input("Your email (Gmail/QQ/163)", key="smtp_email")
    smtp_password = st.text_input("App password", type="password", key="smtp_password",
                                   help="For Gmail: use App Password (not your login password). For QQ: use authorization code (授权码).")
    smtp_server = st.selectbox("Email provider", ["Gmail", "QQ Mail", "163 Mail", "Outlook"],
                                key="smtp_provider")

    st.divider()
    st.markdown("**Available Courses:**")
    for code, info in courses.items():
        st.markdown(f"- `{code}` — {info['name']}")
    st.divider()
    st.markdown(
        "Ask me to:\n"
        "- Look up course info\n"
        "- Build a study plan\n"
        "- Get study tips for a subject\n"
        "- Search the web for any topic\n"
        "- Send study plan to your email"
    )

# ---------------------------------------------------------------------------
# Session state: agent and chat history
# ---------------------------------------------------------------------------

if "chat_history" not in st.session_state:
    st.session_state.chat_history: list[tuple[str, str]] = []

SYSTEM_PROMPT = (
    "You are StudyBuddy, a friendly AI learning coach. "
    "Help students organize their revision.\n\n"
    "IMPORTANT WORKFLOW RULES:\n"
    "1. When a student asks for a study plan: use calculate_study_plan tool immediately with the course code and hours they provide. If they didn't specify hours, default to 3 hours/day.\n"
    "2. When a student asks to send/email something: use the send_email tool immediately. Do NOT ask for confirmation before sending.\n"
    "3. When a student provides their email AND asks for a study plan in the same message: first call calculate_study_plan, then immediately call send_email with the plan content.\n"
    "4. Always use the tools to get exact data. Never make up course information.\n"
    "5. When students ask about topics not in the local course data, use web_search.\n"
    "6. Be encouraging and concise. Don't ask unnecessary follow-up questions.\n"
    "7. If a student gives you a course code and email together, DO NOT ask more questions - just generate the plan and send it.\n\n"
    "Available courses: CS101, MATH201, PHYS150, ENG102, BIO110"
)

TOOLS = [get_course_info, calculate_study_plan, get_study_tips, web_search, send_email]

if "agent" not in st.session_state:
    st.session_state.agent = Agent(
        model="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        tools=TOOLS,
        system_prompt=SYSTEM_PROMPT,
    )

# ---------------------------------------------------------------------------
# Display chat history
# ---------------------------------------------------------------------------

st.title("📚 StudyBuddy")

for role, message in st.session_state.chat_history:
    with st.chat_message(role):
        st.markdown(message)

# ---------------------------------------------------------------------------
# Chat input
# ---------------------------------------------------------------------------

if prompt := st.chat_input("Ask me about your courses, study plans, or tips..."):
    # Display user message
    st.session_state.chat_history.append(("user", prompt))
    with st.chat_message("user"):
        st.markdown(prompt)

    # Build conversation context from history for the agent
    history_context = ""
    if st.session_state.chat_history[:-1]:  # Exclude the current message
        history_lines = []
        for role, msg in st.session_state.chat_history[:-1]:
            prefix = "Student" if role == "user" else "StudyBuddy"
            history_lines.append(f"{prefix}: {msg}")
        history_context = (
            "Previous conversation:\n"
            + "\n".join(history_lines[-10:])  # Last 10 messages for context
            + "\n\nCurrent student message: "
        )

    # Get agent response - create fresh agent to avoid concurrency issues
    agent = Agent(
        model="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        tools=TOOLS,
        system_prompt=SYSTEM_PROMPT,
    )

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            full_prompt = history_context + prompt if history_context else prompt
            response = agent(full_prompt)
            reply = str(response)
        st.markdown(reply)

    st.session_state.chat_history.append(("assistant", reply))
