import io
from django.http import FileResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from django.utils import timezone
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Avg
from .models import QualiteAir
from .serializers import QualiteAirSerializer
from .ml_service import predire_tous_les_indicateurs

class QualiteAirViewSet(viewsets.ModelViewSet):
    queryset = QualiteAir.objects.select_related('ville__region').all().order_by('-date_cible')
    serializer_class = QualiteAirSerializer

    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filterset_fields = ['ville__nom', 'date_cible', 'est_prediction', 'categorie']

    @action(detail=False, methods=['get'], url_path='national_kpis')
    def get_national_kpis(self, request):
        aujourd_hui = timezone.now().date()
        
        donnees_jour = QualiteAir.objects.filter(
            date_cible=aujourd_hui, 
            est_prediction=False
        )

        if not donnees_jour.exists():
            return Response({"message": "Aucune donnée disponible pour aujourd'hui."}, status=200)

        aqi_moyen = donnees_jour.aggregate(Avg('indice_aqi'))['indice_aqi__avg']

        villes_en_danger = donnees_jour.filter(
            categorie__in=['Malsain', 'Tres_malsain', 'Dangereux']
        ).count()

        return Response({
            "date": aujourd_hui,
            "aqi_moyen_national": round(aqi_moyen, 2) if aqi_moyen else 0,
            "nombre_villes_critiques": villes_en_danger,
            "total_villes_scannees": donnees_jour.count()
        })
    
    @action(detail=False, methods=['get'], url_path='reports/pdf')
    def generate_pdf_report(self, request, *args, **kwargs):
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from locations.models import Ville
        from alerts.models import Alerte

        # City filter
        ville_nom = request.query_params.get('ville_nom')
        ville_obj = None
        if ville_nom:
            ville_obj = Ville.objects.filter(nom=ville_nom).first()

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=2*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()
        elements = []

        # Custom styles
        title_style = ParagraphStyle('AirGuardTitle', parent=styles['Title'], fontSize=22, textColor=colors.HexColor('#0F766E'), spaceAfter=6)
        subtitle_style = ParagraphStyle('AirGuardSub', parent=styles['Normal'], fontSize=11, textColor=colors.HexColor('#64748B'), spaceAfter=20)
        heading_style = ParagraphStyle('AirGuardH2', parent=styles['Heading2'], fontSize=14, textColor=colors.HexColor('#134E4A'), spaceBefore=20, spaceAfter=10)
        body_style = ParagraphStyle('AirGuardBody', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor('#1E293B'), spaceAfter=8)
        small_style = ParagraphStyle('AirGuardSmall', parent=styles['Normal'], fontSize=8, textColor=colors.HexColor('#64748B'))

        now = timezone.now()
        date_str = now.strftime("%d/%m/%Y a %H:%M")

        # Title
        elements.append(Paragraph("AirGuard Cameroun", title_style))
        if ville_obj:
            elements.append(Paragraph(f"Rapport qualite de l'air - {ville_obj.nom} - Genere le {date_str}", subtitle_style))
        else:
            elements.append(Paragraph(f"Rapport national de la qualite de l'air - Genere le {date_str}", subtitle_style))

        # KPIs
        if ville_obj:
            elements.append(Paragraph(f"1. Indicateurs pour {ville_obj.nom}", heading_style))
        else:
            elements.append(Paragraph("1. Indicateurs nationaux", heading_style))

        base_qs = QualiteAir.objects.filter(est_prediction=False)
        if ville_obj:
            base_qs = base_qs.filter(ville=ville_obj)

        derniere_date = base_qs.order_by('-date_cible').values_list('date_cible', flat=True).first()
        if derniere_date:
            donnees_jour = base_qs.filter(date_cible=derniere_date)
            total_villes = donnees_jour.count()
            from django.db.models import Count, Q
            stats = donnees_jour.aggregate(
                aqi_avg=Avg('indice_aqi'),
                critiques=Count('id', filter=Q(categorie__in=['Malsain', 'Tres_malsain', 'Dangereux'])),
                bons=Count('id', filter=Q(categorie='Bon')),
                moderes=Count('id', filter=Q(categorie='Modere')),
            )
            aqi_moyen = stats['aqi_avg'] or 0
            critiques = stats['critiques']
            bons = stats['bons']
            moderes = stats['moderes']

            kpi_label = f'AQI moyen - {ville_obj.nom}' if ville_obj else 'AQI moyen national'
            kpi_data = [
                ['Indicateur', 'Valeur'],
                ['Date des donnees', str(derniere_date)],
                [kpi_label, f'{round(aqi_moyen)}'],
                ['Villes surveillees', str(total_villes)],
                ['Villes en zone critique', str(critiques)],
                ['Villes en zone bonne', str(bons)],
                ['Villes en zone moderee', str(moderes)],
            ]
            t = Table(kpi_data, colWidths=[10*cm, 6*cm])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F766E')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F0FDFA')]),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(t)
        else:
            elements.append(Paragraph("Aucune donnee disponible.", body_style))

        # Top 10 worst cities
        if ville_obj:
            elements.append(Paragraph(f"2. Donnees pour {ville_obj.nom}", heading_style))
        else:
            elements.append(Paragraph("2. Top 10 des villes les plus polluees", heading_style))

        if derniere_date:
            top10_qs = base_qs.filter(
                date_cible=derniere_date
            ).select_related('ville__region').order_by('-indice_aqi')
            top10 = top10_qs[:10]

            if top10:
                city_data = [['Rang', 'Ville', 'Region', 'AQI', 'PM2.5 (ug/m3)', 'Categorie']]
                for i, aq in enumerate(top10, 1):
                    city_data.append([
                        str(i),
                        aq.ville.nom,
                        aq.ville.region.nom if hasattr(aq.ville, 'region') else '-',
                        str(aq.indice_aqi),
                        str(round(aq.valeur_pm25, 1)),
                        aq.categorie,
                    ])
                t = Table(city_data, colWidths=[1.5*cm, 3.5*cm, 3.5*cm, 2*cm, 3*cm, 3*cm])
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#134E4A')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F0FDFA')]),
                    ('TOPPADDING', (0, 0), (-1, -1), 5),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ]))
                elements.append(t)

        # Distribution by category
        elements.append(Paragraph("3. Distribution par categorie AQI", heading_style))

        if derniere_date:
            categories = ['Bon', 'Modere', 'Sensible', 'Malsain', 'Tres_malsain', 'Dangereux']
            cat_data = [['Categorie', 'Nombre de villes', 'Pourcentage']]
            for cat in categories:
                count = donnees_jour.filter(categorie=cat).count()
                pct = round(count / total_villes * 100, 1) if total_villes > 0 else 0
                cat_data.append([cat, str(count), f'{pct}%'])
            t = Table(cat_data, colWidths=[5*cm, 5*cm, 5*cm])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F766E')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F0FDFA')]),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            elements.append(t)

        # Active alerts
        elements.append(Paragraph("4. Alertes actives", heading_style))

        alertes_qs = Alerte.objects.filter(est_active=True, statut='publiee').select_related('ville')
        if ville_obj:
            alertes_qs = alertes_qs.filter(ville=ville_obj)
        alertes_actives = alertes_qs
        if alertes_actives.exists():
            alert_data = [['Ville', 'Severite', 'Message']]
            for a in alertes_actives[:10]:
                alert_data.append([a.ville.nom, a.niveau_severite.upper(), a.message_fr[:80]])
            t = Table(alert_data, colWidths=[3*cm, 3*cm, 10*cm])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#EF4444')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#FEF2F2')]),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            elements.append(t)
        else:
            elements.append(Paragraph("Aucune alerte active actuellement.", body_style))

        # Recommendations
        elements.append(Paragraph("5. Recommandations", heading_style))
        elements.append(Paragraph("Sur la base des donnees analysees, les recommandations suivantes sont emises :", body_style))

        recos = [
            "Renforcer la surveillance dans les villes a AQI eleve (> 100).",
            "Informer les populations sensibles (enfants, personnes agees, asthmatiques) dans les zones a risque.",
            "Limiter les activites en exterieur dans les zones critiques.",
            "Poursuivre la collecte de donnees pour ameliorer la precision des predictions.",
            "Envisager des mesures de reduction des emissions dans les zones les plus polluees.",
        ]
        for r in recos:
            elements.append(Paragraph(f"  - {r}", body_style))

        # Footer
        elements.append(Spacer(1, 30))
        elements.append(Paragraph("Ce rapport a ete genere automatiquement par la plateforme AirGuard Cameroun.", small_style))
        elements.append(Paragraph("Hackathon IndabaX Cameroon 2026 - Equipe ML Masters", small_style))

        doc.build(elements)
        buffer.seek(0)
        if ville_obj:
            filename = f'Rapport_AirGuard_{ville_obj.nom}_{now.strftime("%Y%m%d")}.pdf'
        else:
            filename = f'Rapport_AirGuard_National_{now.strftime("%Y%m%d")}.pdf'
        return FileResponse(buffer, as_attachment=True, filename=filename)
    
    @action(detail=False, methods=['post'], url_path='chat', permission_classes=[permissions.AllowAny])
    def chatbot_ia(self, request):
        user_message = request.data.get("message", "").strip().lower()

        if not user_message:
            return Response({"error": "Le message ne peut pas être vide."}, status=400)

        from locations.models import Ville
        from alerts.models import Alerte

        # Detect city in message
        villes = Ville.objects.select_related('region').all()
        ville_trouvee = None
        for v in villes:
            if v.nom.lower() in user_message:
                ville_trouvee = v
                break

        # Get latest data
        derniere_date = QualiteAir.objects.filter(est_prediction=False).order_by('-date_cible').values_list('date_cible', flat=True).first()

        # Build response based on question type
        reply = ""

        if ville_trouvee:
            # City-specific response
            aqi = QualiteAir.objects.filter(ville=ville_trouvee, est_prediction=False).order_by('-date_cible').first()
            alerte = Alerte.objects.filter(ville=ville_trouvee, est_active=True, statut='publiee').first()

            if aqi:
                conseils = {
                    'Bon': "L'air est pur ! Vous pouvez profiter de vos activités en extérieur sans restriction.",
                    'Modere': "L'air est acceptable. Les personnes sensibles (asthmatiques, enfants, personnes âgées) doivent rester vigilantes.",
                    'Sensible': "Attention, l'air est dégradé. Limitez les activités physiques en extérieur. Fermez les fenêtres aux heures de pointe.",
                    'Malsain': "L'air est malsain ! Évitez de sortir. Portez un masque si nécessaire. Fermez les fenêtres.",
                    'Tres_malsain': "DANGER — l'air est très malsain. Restez à l'intérieur. Aucune activité en extérieur. Protégez les enfants et personnes âgées.",
                    'Dangereux': "URGENCE SANITAIRE — ne sortez pas ! Fermez portes et fenêtres. Appelez le 119 en cas de difficulté respiratoire.",
                }
                conseil = conseils.get(aqi.categorie, "")
                reply = (
                    f"À {ville_trouvee.nom} ({ville_trouvee.region.nom}), "
                    f"l'indice de qualité de l'air est de {aqi.indice_aqi} "
                    f"(PM2.5 : {aqi.valeur_pm25:.1f} µg/m³). "
                    f"Catégorie : {aqi.categorie}.\n\n{conseil}"
                )
                if alerte:
                    reply += f"\n\n⚠️ Alerte active : {alerte.message_fr}"
            else:
                reply = f"Je n'ai pas encore de données pour {ville_trouvee.nom}. Les données sont mises à jour régulièrement."

        elif any(mot in user_message for mot in ['alerte', 'danger', 'urgence', 'risque']):
            alertes = Alerte.objects.filter(est_active=True, statut='publiee').select_related('ville')[:5]
            if alertes:
                reply = f"Il y a {len(alertes)} alerte(s) active(s) :\n\n"
                for a in alertes:
                    reply += f"• {a.ville.nom} — {a.niveau_severite.upper()} : {a.message_fr[:100]}\n"
            else:
                reply = "Bonne nouvelle ! Aucune alerte n'est active pour le moment au Cameroun."

        elif any(mot in user_message for mot in ['conseil', 'santé', 'protection', 'masque', 'enfant', 'asthme', 'sport']):
            reply = (
                "Voici des conseils pour protéger votre santé :\n\n"
                "• Consultez l'AQI de votre ville avant de sortir\n"
                "• Les personnes asthmatiques doivent garder leur inhalateur à portée\n"
                "• Évitez le sport en extérieur quand l'AQI dépasse 100\n"
                "• Fermez les fenêtres aux heures de pointe (7h-9h et 17h-19h)\n"
                "• Les enfants et personnes âgées sont les plus vulnérables\n"
                "• Hydratez-vous régulièrement\n"
                "• En cas de gêne respiratoire, consultez un médecin"
            )

        elif any(mot in user_message for mot in ['bonjour', 'salut', 'hello', 'bonsoir']):
            reply = (
                "Bonjour ! Je suis AirGuard Bot, votre assistant qualité de l'air au Cameroun.\n\n"
                "Vous pouvez me poser des questions comme :\n"
                "• « Comment est l'air à Douala ? »\n"
                "• « Y a-t-il des alertes en cours ? »\n"
                "• « Quels conseils pour protéger ma santé ? »\n"
                "• « Quelle est la ville la plus polluée ? »"
            )

        elif any(mot in user_message for mot in ['pire', 'pollu', 'mauvais', 'top']):
            if derniere_date:
                top5 = QualiteAir.objects.filter(
                    date_cible=derniere_date, est_prediction=False
                ).select_related('ville__region').order_by('-indice_aqi')[:5]
                if top5:
                    reply = "Les villes avec la pire qualité de l'air :\n\n"
                    for i, aq in enumerate(top5, 1):
                        reply += f"{i}. {aq.ville.nom} — AQI {aq.indice_aqi} ({aq.categorie})\n"
                else:
                    reply = "Pas de données disponibles pour le moment."
            else:
                reply = "Pas de données disponibles pour le moment."

        elif any(mot in user_message for mot in ['meilleur', 'propre', 'bon', 'sain']):
            if derniere_date:
                top5 = QualiteAir.objects.filter(
                    date_cible=derniere_date, est_prediction=False
                ).select_related('ville__region').order_by('indice_aqi')[:5]
                if top5:
                    reply = "Les villes avec le meilleur air :\n\n"
                    for i, aq in enumerate(top5, 1):
                        reply += f"{i}. {aq.ville.nom} — AQI {aq.indice_aqi} ({aq.categorie})\n"
                else:
                    reply = "Pas de données disponibles pour le moment."
            else:
                reply = "Pas de données disponibles pour le moment."

        else:
            # Default: national summary
            if derniere_date:
                from django.db.models import Avg, Count, Q
                stats = QualiteAir.objects.filter(
                    date_cible=derniere_date, est_prediction=False
                ).aggregate(
                    avg_aqi=Avg('indice_aqi'),
                    critiques=Count('id', filter=Q(categorie__in=['Malsain', 'Tres_malsain', 'Dangereux'])),
                    total=Count('id'),
                )
                avg = round(stats['avg_aqi'] or 0)
                reply = (
                    f"Résumé national ({derniere_date}) :\n\n"
                    f"• AQI moyen : {avg}\n"
                    f"• Villes surveillées : {stats['total']}\n"
                    f"• Villes en zone critique : {stats['critiques']}\n\n"
                    "Posez-moi une question sur une ville précise pour plus de détails !"
                )
            else:
                reply = (
                    "Je suis AirGuard Bot. Je peux vous renseigner sur la qualité de l'air dans les villes du Cameroun. "
                    "Demandez-moi par exemple : « Comment est l'air à Yaoundé ? »"
                )

        return Response({
            "response": reply,
            "source": "AirGuard Bot (ML Masters)"
        })
        
    @action(detail=False, methods=['post'], url_path='predict', permission_classes=[permissions.AllowAny])
    def predict_all_risks(self, request):
        ville_nom = request.data.get('ville_nom')
        meteo_data = request.data.get('meteo_data', {})
        
        if not ville_nom:
            return Response({"error": "Le champ 'ville_nom' est obligatoire."}, status=400)
            
        resultat = predire_tous_les_indicateurs(ville_nom, meteo_data)
        
        if "error" in resultat:
            return Response(resultat, status=400)
            
        return Response(resultat, status=200)