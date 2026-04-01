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
        buffer = io.BytesIO()
        
        p = canvas.Canvas(buffer, pagesize=letter)
        p.setTitle("Rapport AirGuard")
        
        p.setFont("Helvetica-Bold", 16)
        p.drawString(200, 750, "Rapport National - AirGuard Cameroun")
        
        p.setFont("Helvetica", 12)
        date_str = timezone.now().strftime("%d/%m/%Y à %H:%M")
        p.drawString(50, 700, f"Date de génération : {date_str}")
        
        villes_critiques = QualiteAir.objects.filter(
            date_cible=timezone.now().date(),
            categorie__in=['Malsain', 'Tres_malsain', 'Dangereux']
        ).count()
        
        p.drawString(50, 660, f"Nombre de villes en zone critique aujourd'hui : {villes_critiques}")
        p.drawString(50, 640, "Recommandation : Renforcer la surveillance dans les zones à risque.")
        
        p.showPage()
        p.save()
        
        buffer.seek(0)
        return FileResponse(buffer, as_attachment=True, filename='Rapport_AirGuard.pdf')
    
    @action(detail=False, methods=['post'], url_path='chat')
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
        
    @action(detail=False, methods=['post'], url_path='predict')
    def predict_all_risks(self, request):
        ville_nom = request.data.get('ville_nom')
        meteo_data = request.data.get('meteo_data', {})
        
        if not ville_nom:
            return Response({"error": "Le champ 'ville_nom' est obligatoire."}, status=400)
            
        resultat = predire_tous_les_indicateurs(ville_nom, meteo_data)
        
        if "error" in resultat:
            return Response(resultat, status=400)
            
        return Response(resultat, status=200)