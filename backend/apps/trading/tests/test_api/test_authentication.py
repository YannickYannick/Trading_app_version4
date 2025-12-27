"""
Tests d'authentification pour l'API Trading.

Teste :
- Login/Logout Session
- Login/Logout JWT
- Refresh JWT
- Registration
- Protected endpoints
"""
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status


class SessionAuthenticationTests(APITestCase):
    """Tests pour l'authentification par session."""
    
    def setUp(self):
        """Configuration avant chaque test."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_login_with_valid_credentials(self):
        """Test login avec credentials valides."""
        response = self.client.post('/api/auth/login/', {
            'username': 'testuser',
            'password': 'testpass123',
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
        self.assertEqual(response.data['user']['username'], 'testuser')
    
    def test_login_with_invalid_password(self):
        """Test login avec mot de passe invalide."""
        response = self.client.post('/api/auth/login/', {
            'username': 'testuser',
            'password': 'wrongpassword',
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', response.data)
    
    def test_login_with_missing_fields(self):
        """Test login avec champs manquants."""
        response = self.client.post('/api/auth/login/', {
            'username': 'testuser',
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_logout(self):
        """Test logout."""
        # Se connecter d'abord
        self.client.force_authenticate(user=self.user)
        
        response = self.client.post('/api/auth/logout/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')


class JWTAuthenticationTests(APITestCase):
    """Tests pour l'authentification JWT."""
    
    def setUp(self):
        """Configuration avant chaque test."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_jwt_login_returns_tokens(self):
        """Test que le login JWT retourne access et refresh tokens."""
        response = self.client.post('/api/auth/jwt/login/', {
            'username': 'testuser',
            'password': 'testpass123',
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)
    
    def test_jwt_login_with_invalid_credentials(self):
        """Test login JWT avec credentials invalides."""
        response = self.client.post('/api/auth/jwt/login/', {
            'username': 'testuser',
            'password': 'wrongpassword',
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_jwt_access_protected_endpoint(self):
        """Test accès à un endpoint protégé avec JWT."""
        # Obtenir le token
        login_response = self.client.post('/api/auth/jwt/login/', {
            'username': 'testuser',
            'password': 'testpass123',
        }, format='json')
        
        access_token = login_response.data['access']
        
        # Utiliser le token pour accéder à un endpoint protégé
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        response = self.client.get('/api/auth/user/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'testuser')
    
    def test_jwt_refresh_token(self):
        """Test refresh du JWT."""
        # Obtenir les tokens
        login_response = self.client.post('/api/auth/jwt/login/', {
            'username': 'testuser',
            'password': 'testpass123',
        }, format='json')
        
        refresh_token = login_response.data['refresh']
        
        # Rafraîchir le token
        response = self.client.post('/api/auth/jwt/refresh/', {
            'refresh': refresh_token,
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)


class RegistrationTests(APITestCase):
    """Tests pour l'inscription."""
    
    def test_register_new_user(self):
        """Test inscription d'un nouvel utilisateur."""
        response = self.client.post('/api/auth/register/', {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'newpass123',
            'password2': 'newpass123',
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'success')
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertTrue(User.objects.filter(username='newuser').exists())
    
    def test_register_with_mismatched_passwords(self):
        """Test inscription avec mots de passe différents."""
        response = self.client.post('/api/auth/register/', {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'newpass123',
            'password2': 'differentpass',
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_register_with_existing_username(self):
        """Test inscription avec username existant."""
        User.objects.create_user(
            username='existinguser',
            email='existing@example.com',
            password='testpass123'
        )
        
        response = self.client.post('/api/auth/register/', {
            'username': 'existinguser',
            'email': 'new@example.com',
            'password': 'newpass123',
            'password2': 'newpass123',
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_register_with_short_password(self):
        """Test inscription avec mot de passe trop court."""
        response = self.client.post('/api/auth/register/', {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'short',
            'password2': 'short',
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ProtectedEndpointsTests(APITestCase):
    """Tests pour vérifier que les endpoints sont protégés."""
    
    def test_assets_requires_authentication(self):
        """Test que /api/assets/ nécessite une authentification."""
        response = self.client.get('/api/assets/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_positions_requires_authentication(self):
        """Test que /api/positions/ nécessite une authentification."""
        response = self.client.get('/api/positions/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_trades_requires_authentication(self):
        """Test que /api/trades/ nécessite une authentification."""
        response = self.client.get('/api/trades/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_strategies_requires_authentication(self):
        """Test que /api/strategies/ nécessite une authentification."""
        response = self.client.get('/api/strategies/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

