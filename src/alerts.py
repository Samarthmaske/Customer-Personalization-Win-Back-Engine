try:
    from twilio.rest import Client
    from twilio.twiml.voice_response import VoiceResponse
except Exception:
    Client = None

    class VoiceResponse:
        """Minimal fallback for building a spoken message when Twilio is not installed.

        Tests only need a string representation containing the spoken text, so
        this lightweight implementation is sufficient for unit tests.
        """

        def __init__(self):
            self._parts = []

        def say(self, text, **_kwargs):
            self._parts.append(text)

        def __str__(self):
            return " ".join(self._parts)

try:
    from twilio.base.exceptions import TwilioRestException
except ImportError:
    TwilioRestException = Exception

from config import (
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN,
    TWILIO_FROM_NUMBER,
    TWILIO_TO_NUMBER,
)


class AlertManager:
    """Manages alert notifications for animal intrusion detections."""

    def __init__(self):
        self.client = None
        if all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN]):
            try:
                self.client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            except Exception:
                self.client = None

    def _has_twilio_credentials(self) -> bool:
        return all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER, TWILIO_TO_NUMBER])

    def _build_twiml(self, animal_name: str, camera_id: str, distance_km: float) -> str:
        response = VoiceResponse()
        message_text = (
            f"Warning! A high-risk animal, {animal_name}, has been detected near camera {camera_id}. "
            f"Distance to your registered location is {distance_km:.2f} kilometers. "
            "Please stay inside and stay safe."
        )
        response.say(message_text, voice="alice", language="en-US")
        return str(response)

    def send_alert(self, risk_level: str, animal_name: str, distance_km: float, camera_id: str) -> dict:
        """Send an alert based on the evaluated risk level.

        LOW risk returns a dashboard notification message.
        HIGH risk triggers a Twilio voice call when credentials are configured.
        """
        risk_level = risk_level.upper() if risk_level else "LOW"
        alert_message = (
            f"[{risk_level}] Animal detected: {animal_name} near {camera_id}. "
            f"Distance: {distance_km:.2f} km."
        )

        if risk_level == "LOW":
            return {
                "status": "logged",
                "message": alert_message,
            }

        if not self._has_twilio_credentials() or self.client is None:
            return {
                "status": "disabled",
                "message": (
                    "High-risk alert detected, but Twilio credentials are missing or invalid. "
                    f"Notification message: {alert_message}"
                ),
            }

        try:
            twiml = self._build_twiml(animal_name, camera_id, distance_km)
            call = self.client.calls.create(
                twiml=twiml,
                from_=TWILIO_FROM_NUMBER,
                to=TWILIO_TO_NUMBER,
            )
            return {
                "status": "sent",
                "call_sid": call.sid,
                "message": alert_message,
            }
        except TwilioRestException as exc:
            print(f"Twilio API error: {exc}")
            return {
                "status": "error",
                "message": (
                    "Twilio API error occurred. High-risk alert recorded, "
                    "but voice call could not be placed."
                ),
            }
        except Exception as exc:
            return {
                "status": "error",
                "message": f"Failed to initiate Twilio voice call: {exc}",
            }
