# middleware.py
from asgiref.sync import sync_to_async
from channels.middleware import BaseMiddleware
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed
from django.contrib.auth.models import AnonymousUser

class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        try:
            # Extract the token from the query string or headers
            query_string = scope.get('query_string', b'').decode('utf-8')
            token = None
            for part in query_string.split('&'):
                if part.startswith('token='):
                    token = part.split('=')[1]
                    break

            if token:
                # Authenticate the token using SimpleJWT
                jwt_auth = JWTAuthentication()
                validated_token = jwt_auth.get_validated_token(token)
                user = await self.get_user(jwt_auth, validated_token)
                scope['user'] = user
            else:
                scope['user'] = AnonymousUser()
        except (InvalidToken, AuthenticationFailed):
            scope['user'] = AnonymousUser()

        return await super().__call__(scope, receive, send)

    @sync_to_async
    def get_user(self, jwt_auth, validated_token):
        # print(jwt_auth)
        # print(validated_token)
        # Synchronous ORM call to get the user
        return jwt_auth.get_user(validated_token)