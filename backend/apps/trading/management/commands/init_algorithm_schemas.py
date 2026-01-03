"""
Command Django pour initialiser les schémas d'algorithmes.

Usage:
    python manage.py init_algorithm_schemas
    python manage.py init_algorithm_schemas --init-existing
    python manage.py init_algorithm_schemas --force
"""
from django.core.management.base import BaseCommand
from apps.trading.models import AlgorithmSchema, AlgorithmParameterDefinition, Strategy


class Command(BaseCommand):
    help = 'Initialise les schémas d\'algorithmes avec leurs paramètres par défaut'

    def add_arguments(self, parser):
        parser.add_argument(
            '--init-existing',
            action='store_true',
            help='Initialise aussi les paramètres pour les stratégies existantes',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Écrase les schémas existants',
        )

    def handle(self, *args, **options):
        force = options['force']
        init_existing = options['init_existing']

        # Définition des schémas d'algorithmes
        algorithms_data = {
            'threshold': {
                'name': 'Threshold',
                'description': 'Algorithme de seuils : Acheter en dessous de X1, vendre au-dessus de X2',
                'parameters': [
                    {'key': 'threshold_low', 'param_type': 'float', 'default_value': '100.0', 'required': True, 'description': 'Seuil bas : prix en dessous = signal d\'achat'},
                    {'key': 'threshold_high', 'param_type': 'float', 'default_value': '200.0', 'required': True, 'description': 'Seuil haut : prix au-dessus = signal de vente'},
                    {'key': 'order_size', 'param_type': 'float', 'default_value': '1.0', 'required': True, 'description': 'Taille maximale d\'un ordre (limite de sécurité)'},
                    {'key': 'stop_loss', 'param_type': 'float', 'default_value': '0.05', 'required': True, 'description': 'Stop-loss (5%)'},
                ]
            },
            'ma_crossover': {
                'name': 'Moving Average Crossover',
                'description': 'Algorithme de croisement de moyennes mobiles',
                'parameters': [
                    {'key': 'ma1_period', 'param_type': 'int', 'default_value': '20', 'required': True, 'description': 'Période de la moyenne mobile rapide'},
                    {'key': 'ma2_period', 'param_type': 'int', 'default_value': '50', 'required': True, 'description': 'Période de la moyenne mobile lente'},
                    {'key': 'order_size', 'param_type': 'float', 'default_value': '1.0', 'required': True, 'description': 'Taille maximale d\'un ordre'},
                    {'key': 'stop_loss', 'param_type': 'float', 'default_value': '0.05', 'required': True, 'description': 'Stop-loss (5%)'},
                ]
            },
            'rsi': {
                'name': 'RSI',
                'description': 'Algorithme RSI (Relative Strength Index)',
                'parameters': [
                    {'key': 'rsi_period', 'param_type': 'int', 'default_value': '14', 'required': True, 'description': 'Période pour le calcul du RSI'},
                    {'key': 'rsi_low', 'param_type': 'int', 'default_value': '30', 'required': True, 'description': 'Seuil bas RSI : en dessous = survente (achat)'},
                    {'key': 'rsi_high', 'param_type': 'int', 'default_value': '70', 'required': True, 'description': 'Seuil haut RSI : au-dessus = surachat (vente)'},
                    {'key': 'order_size', 'param_type': 'float', 'default_value': '1.0', 'required': True, 'description': 'Taille maximale d\'un ordre'},
                    {'key': 'stop_loss', 'param_type': 'float', 'default_value': '0.05', 'required': True, 'description': 'Stop-loss (5%)'},
                ]
            },
            'bollinger': {
                'name': 'Bollinger Bands',
                'description': 'Algorithme des bandes de Bollinger',
                'parameters': [
                    {'key': 'bb_period', 'param_type': 'int', 'default_value': '20', 'required': True, 'description': 'Période pour la moyenne mobile des bandes'},
                    {'key': 'bb_std', 'param_type': 'float', 'default_value': '2.0', 'required': True, 'description': 'Nombre d\'écarts-types pour les bandes'},
                    {'key': 'order_size', 'param_type': 'float', 'default_value': '1.0', 'required': True, 'description': 'Taille maximale d\'un ordre'},
                    {'key': 'stop_loss', 'param_type': 'float', 'default_value': '0.05', 'required': True, 'description': 'Stop-loss (5%)'},
                ]
            },
            'macd': {
                'name': 'MACD',
                'description': 'Algorithme MACD (Moving Average Convergence Divergence)',
                'parameters': [
                    {'key': 'macd_fast', 'param_type': 'int', 'default_value': '12', 'required': True, 'description': 'Période EMA rapide pour MACD'},
                    {'key': 'macd_slow', 'param_type': 'int', 'default_value': '26', 'required': True, 'description': 'Période EMA lente pour MACD'},
                    {'key': 'macd_signal', 'param_type': 'int', 'default_value': '9', 'required': True, 'description': 'Période EMA pour la ligne de signal'},
                    {'key': 'order_size', 'param_type': 'float', 'default_value': '1.0', 'required': True, 'description': 'Taille maximale d\'un ordre'},
                    {'key': 'stop_loss', 'param_type': 'float', 'default_value': '0.05', 'required': True, 'description': 'Stop-loss (5%)'},
                ]
            },
            'grid': {
                'name': 'Grid Trading',
                'description': 'Algorithme de Grid Trading',
                'parameters': [
                    {'key': 'grid_min', 'param_type': 'float', 'default_value': '100.0', 'required': True, 'description': 'Prix minimum de la grille'},
                    {'key': 'grid_max', 'param_type': 'float', 'default_value': '200.0', 'required': True, 'description': 'Prix maximum de la grille'},
                    {'key': 'grid_levels', 'param_type': 'int', 'default_value': '10', 'required': True, 'description': 'Nombre de niveaux dans la grille'},
                    {'key': 'order_size', 'param_type': 'float', 'default_value': '1.0', 'required': True, 'description': 'Taille maximale d\'un ordre'},
                    {'key': 'stop_loss', 'param_type': 'float', 'default_value': '0.05', 'required': True, 'description': 'Stop-loss (5%)'},
                ]
            },
        }

        created_count = 0
        updated_count = 0

        for algorithm_type, data in algorithms_data.items():
            # Créer ou mettre à jour le schéma
            schema, created = AlgorithmSchema.objects.update_or_create(
                algorithm_type=algorithm_type,
                defaults={
                    'name': data['name'],
                    'description': data['description'],
                }
            )

            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'✓ Schéma créé : {schema.name} ({algorithm_type})'))
            else:
                if force:
                    schema.name = data['name']
                    schema.description = data['description']
                    schema.save()
                    updated_count += 1
                    self.stdout.write(self.style.WARNING(f'↻ Schéma mis à jour : {schema.name} ({algorithm_type})'))
                else:
                    self.stdout.write(self.style.WARNING(f'○ Schéma déjà existant : {schema.name} ({algorithm_type})'))

            # Créer ou mettre à jour les définitions de paramètres
            for param_data in data['parameters']:
                AlgorithmParameterDefinition.objects.update_or_create(
                    schema=schema,
                    key=param_data['key'],
                    defaults={
                        'param_type': param_data['param_type'],
                        'default_value': param_data['default_value'],
                        'required': param_data['required'],
                        'description': param_data['description'],
                    }
                )

            self.stdout.write(f'  → {len(data["parameters"])} paramètres définis')

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'✓ {created_count} schéma(s) créé(s), {updated_count} mis à jour'))

        # Initialiser les paramètres pour les stratégies existantes
        if init_existing:
            self.stdout.write('')
            self.stdout.write('Initialisation des paramètres pour les stratégies existantes...')
            strategies = Strategy.objects.filter(algorithm_type__isnull=False).exclude(algorithm_type='')
            initialized_count = 0

            for strategy in strategies:
                try:
                    strategy.initialize_default_parameters()
                    initialized_count += 1
                    self.stdout.write(f'  ✓ {strategy.name}')
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'  ✗ {strategy.name}: {e}'))

            self.stdout.write(self.style.SUCCESS(f'✓ {initialized_count} stratégie(s) initialisée(s)'))



