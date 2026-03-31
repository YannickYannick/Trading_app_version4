# Instructions pour appliquer les migrations

## Étapes à suivre

1. **Activer l'environnement virtuel** (si vous en avez un)
   ```bash
   # Windows PowerShell
   .\venv\Scripts\Activate.ps1
   
   # Ou Windows CMD
   venv\Scripts\activate.bat
   
   # Linux/Mac
   source venv/bin/activate
   ```

2. **Créer la migration**
   ```bash
   cd backend
   python manage.py makemigrations trading
   ```

3. **Appliquer la migration**
   ```bash
   python manage.py migrate
   ```

4. **Initialiser les schémas d'algorithmes**
   ```bash
   python manage.py init_algorithm_schemas
   ```

5. **Vérifier que tout fonctionne**
   - Aller dans l'admin Django : http://127.0.0.1:8000/admin/
   - Vérifier que les nouveaux modèles apparaissent :
     - Algorithm Schemas
     - Algorithm Parameters
     - Strategy (avec le nouveau champ algorithm_type)
   - Créer une nouvelle stratégie et vérifier qu'on peut sélectionner un algorithm_type

## Si vous avez des erreurs

### Erreur : numpy ou pandas non installés
```bash
pip install numpy pandas
```

### Erreur : Migration ne se crée pas
- Vérifier que les modèles sont bien importés dans `models/__init__.py`
- Vérifier qu'il n'y a pas d'erreurs de syntaxe dans `strategies.py`

### Erreur : Migration ne s'applique pas
- Vérifier les logs pour voir l'erreur exacte
- Vérifier que la base de données est accessible



