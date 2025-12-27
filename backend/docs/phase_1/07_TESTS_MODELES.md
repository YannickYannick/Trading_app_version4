# 🧪 Tests des modèles

## Structure des tests

```
apps/trading/tests/
├── __init__.py
├── test_models.py      # Tests des modèles (à créer)
└── test_api/           # Tests API (Phase 2)
```

## Tests de base recommandés

### Test création de modèle

```python
from django.test import TestCase
from django.contrib.auth.models import User
from decimal import Decimal

from apps.trading.models import AllAssets, Asset, Position, Broker


class AllAssetsModelTest(TestCase):
    """Tests pour le modèle AllAssets."""
    
    def test_create_all_asset(self):
        """Test création d'un AllAssets."""
        asset = AllAssets.objects.create(
            symbol='AAPL',
            name='Apple Inc.',
            platform='SAXO',
            asset_type='STOCK',
            market='NASDAQ'
        )
        
        self.assertEqual(asset.symbol, 'AAPL')
        self.assertEqual(asset.platform, 'SAXO')
        self.assertTrue(asset.is_tradable)
    
    def test_unique_together_constraint(self):
        """Test contrainte unique symbol + platform."""
        AllAssets.objects.create(
            symbol='AAPL',
            name='Apple Inc.',
            platform='SAXO',
            asset_type='STOCK',
            market='NASDAQ'
        )
        
        with self.assertRaises(Exception):
            AllAssets.objects.create(
                symbol='AAPL',
                name='Apple Inc. Duplicate',
                platform='SAXO',  # Même platform
                asset_type='STOCK',
                market='NASDAQ'
            )
    
    def test_str_representation(self):
        """Test __str__ du modèle."""
        asset = AllAssets.objects.create(
            symbol='AAPL',
            name='Apple Inc.',
            platform='SAXO',
            asset_type='STOCK',
            market='NASDAQ'
        )
        
        self.assertEqual(str(asset), 'AAPL (SAXO) - Apple Inc.')


class PositionModelTest(TestCase):
    """Tests pour le modèle Position."""
    
    def setUp(self):
        """Configuration commune."""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.broker = Broker.objects.create(
            name='Saxo Bank',
            broker_type='SAXO',
            is_active=True
        )
        self.asset = Asset.objects.create(
            symbol='AAPL',
            name='Apple Inc.',
            asset_type='STOCK',
            currency='USD',
            current_price=Decimal('150.00'),
            is_active=True
        )
    
    def test_pnl_calculation_long(self):
        """Test calcul P&L position LONG."""
        position = Position.objects.create(
            user=self.user,
            asset=self.asset,
            broker=self.broker,
            side='LONG',
            quantity=Decimal('10'),
            entry_price=Decimal('100.00'),
            current_price=Decimal('110.00'),
            is_open=True
        )
        
        # P&L = (110 - 100) * 10 = 100
        self.assertEqual(position.pnl, Decimal('100.00'))
    
    def test_pnl_calculation_short(self):
        """Test calcul P&L position SHORT."""
        position = Position.objects.create(
            user=self.user,
            asset=self.asset,
            broker=self.broker,
            side='SHORT',
            quantity=Decimal('10'),
            entry_price=Decimal('100.00'),
            current_price=Decimal('90.00'),
            is_open=True
        )
        
        # P&L SHORT = (100 - 90) * 10 = 100 (gain quand le prix baisse)
        self.assertEqual(position.pnl, Decimal('100.00'))
```

## Exécuter les tests

```bash
# Tous les tests
python manage.py test

# Tests d'une app
python manage.py test apps.trading

# Tests d'un fichier
python manage.py test apps.trading.tests.test_models

# Tests d'une classe
python manage.py test apps.trading.tests.test_models.PositionModelTest

# Avec verbosité
python manage.py test --verbosity=2
```

## Bonnes pratiques

1. **setUp() pour la configuration commune**
   ```python
   def setUp(self):
       self.user = User.objects.create_user(...)
   ```

2. **Noms descriptifs**
   ```python
   def test_position_pnl_is_positive_when_long_and_price_increases(self):
   ```

3. **Un test = une assertion principale**

4. **Tester les cas limites**
   - Valeurs nulles
   - Contraintes uniques
   - Validations

5. **Utiliser des fixtures pour les données complexes**
   ```python
   from django.test import TestCase
   
   class MyTest(TestCase):
       fixtures = ['test_data.json']
   ```

## Coverage

Pour mesurer la couverture des tests :

```bash
pip install coverage

coverage run manage.py test
coverage report
coverage html  # Génère un rapport HTML
```

