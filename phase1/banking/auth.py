import hashlib
import hmac
import secrets


class AuthenticationService:

    def __init__(self):
        self.users = {}
        self.sessions = {}

        # Mock users for testing
        mock_users = {

            "kasun": {
                "full_name": "Kasun Perera",
                "password": "kasun123",
                "account_id": "ACC001"
            },

            "nimal": {
                "full_name": "Nimal Fernando",
                "password": "nimal123",
                "account_id": "ACC002"
            }
        }

        # Store salted password hashes
        for username, details in mock_users.items():

            salt = secrets.token_bytes(16)

            password_hash = self.hash_password(
                details["password"], salt
            )

            self.users[username] = {
                "full_name": details["full_name"],
                "account_id": details["account_id"],
                "salt": salt,
                "password_hash": password_hash
            }

    def hash_password(self, password, salt):
        return hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt, 200000
        )

    def login(self, username, password):

        username = username.strip().lower()
        user = self.users.get(username)

        # Check the username and password
        if user is None:
            print("Failed login attempt:", username)

            return {
                "success": False,
                "message": "Invalid credentials"
            }

        entered_hash = self.hash_password(
            password, user["salt"]
        )

        if not hmac.compare_digest(
            entered_hash, user["password_hash"]
        ):
            print("Failed login attempt:", username)

            return {
                "success": False,
                "message": "Invalid credentials"
            }

        # Generate a session token
        token = secrets.token_urlsafe(32)
        self.sessions[token] = username

        print("User logged in:", username)

        return {
            "success": True,
            "message": "Login successful",
            "full_name": user["full_name"],
            "token": token
        }

    def get_username(self, token):

        # Find the user linked to the session token
        return self.sessions.get(token)

    def get_account_id(self, username):

        # Get the user's bank account ID
        return self.users[username]["account_id"]
