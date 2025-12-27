"""
Vues d'authentification pour l'API.

Supporte :
- Session Authentication (navigateur)
- JWT Authentication (apps mobiles/API)
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken


# ============================================
# SESSION AUTHENTICATION (Navigateur)
# ============================================

@api_view(['POST'])
@permission_classes([AllowAny])
def login_session(request):
    """
    POST /api/auth/login/
    
    Login avec session (pour le navigateur).
    Body: {"username": "...", "password": "..."}
    """
    username = request.data.get('username')
    password = request.data.get('password')
    
    if not username or not password:
        return Response(
            {'error': 'Username and password required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user = authenticate(request, username=username, password=password)
    
    if user is not None:
        login(request, user)
        return Response({
            'status': 'success',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
            }
        })
    
    return Response(
        {'error': 'Invalid credentials'},
        status=status.HTTP_401_UNAUTHORIZED
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_session(request):
    """
    POST /api/auth/logout/
    
    Logout de la session.
    """
    logout(request)
    return Response({'status': 'success', 'message': 'Logged out successfully'})


# ============================================
# JWT AUTHENTICATION (Apps/API)
# ============================================

@api_view(['POST'])
@permission_classes([AllowAny])
def login_jwt(request):
    """
    POST /api/auth/jwt/login/
    
    Login avec JWT (pour les apps).
    Body: {"username": "...", "password": "..."}
    
    Retourne: {"access": "...", "refresh": "...", "user": {...}}
    """
    username = request.data.get('username')
    password = request.data.get('password')
    
    if not username or not password:
        return Response(
            {'error': 'Username and password required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user = authenticate(request, username=username, password=password)
    
    if user is not None:
        # Générer les tokens JWT
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
            }
        })
    
    return Response(
        {'error': 'Invalid credentials'},
        status=status.HTTP_401_UNAUTHORIZED
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_jwt(request):
    """
    POST /api/auth/jwt/logout/
    
    Blacklist le refresh token pour invalider la session JWT.
    Body: {"refresh": "..."}
    """
    try:
        refresh_token = request.data.get('refresh')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        return Response({'status': 'success', 'message': 'Token blacklisted'})
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


# ============================================
# USER INFO
# ============================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_info(request):
    """
    GET /api/auth/user/
    
    Récupère les informations de l'utilisateur connecté.
    """
    user = request.user
    return Response({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'is_staff': user.is_staff,
        'date_joined': user.date_joined.isoformat(),
        'last_login': user.last_login.isoformat() if user.last_login else None,
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """
    POST /api/auth/register/
    
    Crée un nouveau compte utilisateur.
    Body: {"username": "...", "email": "...", "password": "...", "password2": "..."}
    """
    username = request.data.get('username')
    email = request.data.get('email')
    password = request.data.get('password')
    password2 = request.data.get('password2')
    
    # Validations
    if not all([username, email, password, password2]):
        return Response(
            {'error': 'All fields are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if password != password2:
        return Response(
            {'error': 'Passwords do not match'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if len(password) < 8:
        return Response(
            {'error': 'Password must be at least 8 characters'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if User.objects.filter(username=username).exists():
        return Response(
            {'error': 'Username already exists'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if User.objects.filter(email=email).exists():
        return Response(
            {'error': 'Email already exists'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Créer l'utilisateur
    user = User.objects.create_user(
        username=username,
        email=email,
        password=password
    )
    
    # Générer les tokens JWT pour login automatique
    refresh = RefreshToken.for_user(user)
    
    return Response({
        'status': 'success',
        'message': 'Account created successfully',
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
        }
    }, status=status.HTTP_201_CREATED)

