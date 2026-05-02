# Generated manually for portfolio min/max (actions en portefeuille)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("trading", "0024_allassets_industry_allassets_sector"),
    ]

    operations = [
        migrations.AddField(
            model_name="strategy",
            name="portfolio_min_quantity",
            field=models.DecimalField(
                decimal_places=10,
                default=0,
                help_text="Plancher de position (nombre d'actions/titres à ne pas vendre en dessous) pour l'exécution threshold.",
                max_digits=20,
            ),
        ),
        migrations.AddField(
            model_name="strategy",
            name="portfolio_max_quantity",
            field=models.DecimalField(
                blank=True,
                decimal_places=10,
                help_text="Plafond de position (nombre max d'actions/titres détenus). Vide = illimité.",
                max_digits=20,
                null=True,
            ),
        ),
    ]
