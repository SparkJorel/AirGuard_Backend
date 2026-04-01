import io
from django.http import FileResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from openai import OpenAI
from django.utils import timezone
from django.conf import settings
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Avg
from .models import QualiteAir
from .serializers import QualiteAirSerializer
from .ml_service import predire_tous_les_indicateurs

class QualiteAirViewSet(viewsets.ModelViewSet):
    queryset = QualiteAir.objects.all().order_by('-date_cible')
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
        elements.append(Paragraph(f"Rapport national de la qualite de l'air - Genere le {date_str}", subtitle_style))

        # KPIs
        elements.append(Paragraph("1. Indicateurs nationaux", heading_style))

        derniere_date = QualiteAir.objects.filter(est_prediction=False).order_by('-date_cible').values_list('date_cible', flat=True).first()
        if derniere_date:
            donnees_jour = QualiteAir.objects.filter(date_cible=derniere_date, est_prediction=False)
            total_villes = donnees_jour.count()
            aqi_moyen = donnees_jour.aggregate(Avg('indice_aqi'))['indice_aqi__avg'] or 0
            critiques = donnees_jour.filter(categorie__in=['Malsain', 'Tres_malsain', 'Dangereux']).count()
            bons = donnees_jour.filter(categorie='Bon').count()
            moderes = donnees_jour.filter(categorie='Modere').count()

            kpi_data = [
                ['Indicateur', 'Valeur'],
                ['Date des donnees', str(derniere_date)],
                ['AQI moyen national', f'{round(aqi_moyen)}'],
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
        elements.append(Paragraph("2. Top 10 des villes les plus polluees", heading_style))

        if derniere_date:
            top10 = QualiteAir.objects.filter(
                date_cible=derniere_date, est_prediction=False
            ).select_related('ville').order_by('-indice_aqi')[:10]

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

        alertes_actives = Alerte.objects.filter(est_active=True, statut='publiee').select_related('ville')
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
        filename = f'Rapport_AirGuard_{now.strftime("%Y%m%d")}.pdf'
        return FileResponse(buffer, as_attachment=True, filename=filename)
    
    @action(detail=False, methods=['post'], url_path='chat', permission_classes=[permissions.AllowAny])
    def chatbot_ia(self, request):
        user_message = request.data.get("message", "").strip()
        
        if not user_message:
            return Response({"error": "Le message ne peut pas être vide."}, status=400)

        if not settings.OPENAI_API_KEY:
            return Response({
                "response": "L'intégration IA est en cours de configuration. Dès que la clé API sera insérée, je répondrai intelligemment à vos requêtes sur la qualité de l'air !",
                "source": "AirGuard Bot"
            })

        try:
            client = OpenAI(api_key=settings.OPENAI_API_KEY)

            system_prompt = (
                "Tu es AirGuard, un assistant virtuel expert en qualité de l'air, climat et santé publique au Cameroun. "
                "Tu t'adresses à des citoyens. Tes réponses doivent être concises, bienveillantes et proposer des "
                "solutions pratiques (ex: asthme, sport, enfants). Si on te parle d'une ville (Yaoundé, Douala, Maroua...), "
                "adapte-toi au contexte climatique local."
            )

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=200,
                temperature=0.7
            )

            bot_reply = response.choices[0].message.content.strip()
            
            return Response({
                "response": bot_reply,
                "source": "AirGuard Bot (Powered by ML Masters)"
            })
            
        except Exception as e:
            return Response({
                "error": "Le service IA est temporairement indisponible.",
                "details": str(e)
            }, status=503)
        
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