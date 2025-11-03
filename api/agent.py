import json
import os
import re
from datetime import datetime, timedelta
from urllib.parse import quote

# Vercel Python serverless function
# Expects POST with JSON { "text": "..." }
# Returns JSON: { "response_text": str, "actions": [ ... ] }

CONTACT_ENV_MAP = {
    'daddy': 'DADDY_PHONE',
    'dad': 'DADDY_PHONE',
    'father': 'DADDY_PHONE',
    'mom': 'MOM_PHONE',
    'mother': 'MOM_PHONE',
    'wife': 'WIFE_PHONE',
    'husband': 'HUSBAND_PHONE',
}

MONTHS = {
    'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
    'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12
}

ORDINAL_SUFFIX_RE = re.compile(r"(\d+)(st|nd|rd|th)")
TIME_RE = re.compile(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?")


def remove_wake_words(text: str) -> str:
    lowered = text.lower().strip()
    lowered = re.sub(r"\bhey\s+jarvis\b", "", lowered)
    lowered = re.sub(r"\bjarvis\b", "", lowered)
    return lowered.strip()


def find_contact_number(name: str) -> str | None:
    env_key = CONTACT_ENV_MAP.get(name.lower())
    if env_key:
        return os.getenv(env_key)
    # Also allow direct env by uppercasing name and adding _PHONE
    fallback_key = f"{re.sub('[^A-Za-z0-9]', '_', name).upper()}_PHONE"
    return os.getenv(fallback_key)


def build_maps_url(destination: str) -> str:
    return (
        f"https://www.google.com/maps/dir/?api=1&destination={quote(destination)}"
        "&travelmode=driving&dir_action=navigate"
    )


def normalize_ordinals(s: str) -> str:
    return ORDINAL_SUFFIX_RE.sub(r"\\1", s)


def parse_datetime_from_text(text: str) -> datetime | None:
    # Very lightweight parser: looks for patterns like "on 4th november at 2 pm"
    # or "4 november 2 pm", etc.
    t = normalize_ordinals(text.lower())
    # Extract day
    day_match = re.search(r"\b(\d{1,2})\b", t)
    if not day_match:
        return None
    day = int(day_match.group(1))

    # Extract month
    month = None
    for name, idx in MONTHS.items():
        if name in t:
            month = idx
            break
    if not month:
        return None

    # Extract time
    tm = TIME_RE.search(t)
    if tm:
        hour = int(tm.group(1))
        minute = int(tm.group(2) or 0)
        ampm = tm.group(3)
        if ampm:
            if ampm == 'pm' and hour != 12:
                hour += 12
            if ampm == 'am' and hour == 12:
                hour = 0
    else:
        # default time if not specified
        hour, minute = 9, 0

    now = datetime.now()
    year = now.year
    try:
        dt = datetime(year, month, day, hour, minute)
    except ValueError:
        return None

    # If the date/time is in the past, roll to next year
    if dt < now - timedelta(minutes=1):
        try:
            dt = datetime(year + 1, month, day, hour, minute)
        except ValueError:
            return None
    return dt


def build_calendar_url(title: str, start: datetime, end: datetime, details: str = '', location: str = '') -> str:
    def fmt(d: datetime) -> str:
        return d.strftime('%Y%m%dT%H%M%S')
    params = {
        'action': 'TEMPLATE',
        'text': title,
        'dates': f"{fmt(start)}/{fmt(end)}",
    }
    if details:
        params['details'] = details
    if location:
        params['location'] = location
    # Manual construction to keep simple
    base = 'https://calendar.google.com/calendar/render'
    parts = [f"{k}={quote(v)}" for k, v in params.items()]
    return base + '?' + '&'.join(parts)


def parse_intent(text: str) -> dict:
    t = remove_wake_words(text)
    lowered = t.lower()

    # CALL intent
    if re.search(r"\b(call|dial|phone)\b", lowered):
        # Heuristics: last word after call ... is name/number
        name_match = re.search(r"\b(call|dial|phone)\b\s+(.+)$", lowered)
        contact = None
        if name_match:
            candidate = name_match.group(2).strip()
            # If contains digits, assume it's a direct phone number
            if re.search(r"\d", candidate):
                contact = candidate
            else:
                number = find_contact_number(candidate)
                if number:
                    contact = number
                else:
                    # Try just the last token as a name key
                    tokens = re.split(r"\s+", candidate)
                    if tokens:
                        number = find_contact_number(tokens[-1])
                        if number:
                            contact = number
        if contact:
            return {
                'response_text': f"Calling {contact}.",
                'actions': [
                    { 'type': 'call', 'phone': contact }
                ]
            }
        else:
            return {
                'response_text': "I couldn't find that contact. Set an environment variable like DADDY_PHONE.",
                'actions': [ { 'type': 'message', 'text': 'Missing contact mapping' } ]
            }

    # MAPS intent
    if ('map' in lowered or 'maps' in lowered or 'navigate' in lowered or 'direction' in lowered):
        # extract destination after 'to'
        dest = None
        m = re.search(r"\bto\s+(.+)$", t, flags=re.IGNORECASE)
        if m:
            dest = m.group(1).strip().rstrip('.')
        if not dest:
            # fallback: after 'maps' word
            m2 = re.search(r"maps?\s+(?:to\s+)?(.+)$", t, flags=re.IGNORECASE)
            if m2:
                dest = m2.group(1).strip().rstrip('.')
        if dest:
            url = build_maps_url(dest)
            return {
                'response_text': f"Starting directions to {dest}.",
                'actions': [ { 'type': 'open_url', 'url': url } ]
            }
        else:
            return {
                'response_text': "Where should I navigate to? Say for example: navigate to Sadar Bazaar Chatgali.",
                'actions': []
            }

    # APPOINTMENT intent
    if any(k in lowered for k in ['appointment', 'schedule', 'book', 'reserve']):
        dt = parse_datetime_from_text(lowered)
        title = 'Appointment'
        # Try infer title from domain words
        if 'hair' in lowered and 'salon' in lowered:
            title = 'Hair Salon Appointment'
        elif 'doctor' in lowered:
            title = 'Doctor Appointment'
        elif 'dentist' in lowered:
            title = 'Dentist Appointment'
        if dt:
            end = dt + timedelta(hours=1)
            url = build_calendar_url(title=title, start=dt, end=end, details='Created by Jarvis', location=title.replace(' Appointment',''))
            return {
                'response_text': f"Creating calendar event: {title} at {dt.strftime('%-I:%M %p on %B %d')}.",
                'actions': [ { 'type': 'create_calendar', 'url': url } ]
            }
        else:
            return {
                'response_text': "What date and time? For example: on 4th November at 2 pm.",
                'actions': []
            }

    # Default fallback
    return {
        'response_text': "I heard you. For now I can call, navigate with Google Maps, or schedule an appointment.",
        'actions': []
    }


def handler(request):
    # Vercel Python entrypoint
    if request.method != 'POST':
        return {
            'statusCode': 405,
            'headers': { 'Content-Type': 'application/json' },
            'body': json.dumps({ 'error': 'Method not allowed' })
        }

    try:
        body = request.body.decode('utf-8') if isinstance(request.body, (bytes, bytearray)) else request.body
        payload = json.loads(body or '{}')
        text = payload.get('text') or ''
        if not text.strip():
            raise ValueError('Missing text')
        result = parse_intent(text)
        return {
            'statusCode': 200,
            'headers': { 'Content-Type': 'application/json' },
            'body': json.dumps(result)
        }
    except Exception as e:
        return {
            'statusCode': 400,
            'headers': { 'Content-Type': 'application/json' },
            'body': json.dumps({ 'error': str(e) })
        }
