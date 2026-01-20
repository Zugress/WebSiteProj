import jwt
import datetime
from functools import wraps
from flask import request, jsonify

class JWTManager:
    SECRET_KEY = "987654321"
    ACCESS_TOKEN_EXPIRES = datetime.timedelta(minutes=15)
    REFRESH_TOKEN_EXPIRES = datetime.timedelta(days=7)
    
    @staticmethod
    def create_access_token(user_id, username):
        payload = {
            'user_id': user_id,
            'username': username,
            'exp': datetime.datetime.utcnow() + JWTManager.ACCESS_TOKEN_EXPIRES,
            'iat': datetime.datetime.utcnow(),
            'type': 'access'
        }
        return jwt.encode(payload, JWTManager.SECRET_KEY, algorithm='HS256')
    
    @staticmethod
    def create_refresh_token(user_id, username):
        payload = {
            'user_id': user_id,
            'username': username,
            'exp': datetime.datetime.utcnow() + JWTManager.REFRESH_TOKEN_EXPIRES,
            'iat': datetime.datetime.utcnow(),
            'type': 'refresh'
        }
        return jwt.encode(payload, JWTManager.SECRET_KEY, algorithm='HS256')
    
    @staticmethod
    def verify_token(token):
        try:
            payload = jwt.decode(token, JWTManager.SECRET_KEY, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            return {'error': 'Token expired'}
        except jwt.InvalidTokenError:
            return {'error': 'Invalid token'}
    
    @staticmethod
    def verify_access_token(token):
        payload = JWTManager.verify_token(token)
        if isinstance(payload, dict) and payload.get('type') == 'access':
            return payload
        return None
    
    @staticmethod
    def verify_refresh_token(token):
        payload = JWTManager.verify_token(token)
        if isinstance(payload, dict) and payload.get('type') == 'refresh':
            return payload
        return None

def jwt_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'error': 'Authorization header is missing'}), 401
        
        try:
            auth_token = auth_header.split(" ")[1]
        except IndexError:
            return jsonify({'error': 'Bearer token malformed'}), 401
        
        payload = JWTManager.verify_access_token(auth_token)
        if not payload or 'error' in payload:
            error_msg = payload.get('error') if payload and isinstance(payload, dict) else 'Invalid token'
            return jsonify({'error': error_msg}), 401
        
        request.user_id = payload['user_id']
        request.username = payload['username']
        
        return f(*args, **kwargs)
    return decorated_function