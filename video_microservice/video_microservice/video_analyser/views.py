from django.shortcuts import render
from django.http import JsonResponse,HttpResponse
from django.views import View
# Create your views here.
from .scorecalc import *
from bson import ObjectId
from pymongo import MongoClient


def test(request):
    return HttpResponse("Testing completed!")

class VideoView(View):
    def get(self, request, talentId, *args, **kwargs):
        scores = combined_score_calculator(talentId)
    
        if scores is not None:
            language_ability_score, fluency_score, confidence_label = scores
        else:
            language_ability_score, fluency_score = 0, 0
            confidence_label=None
            
            print("Error: Unable to calculate scores.")
            return None
        

        response_data = {
            'language_ability_score': language_ability_score,
            'fluency_score': fluency_score,
            'confidence_level':confidence_label
        }
        
        try:
            client = MongoClient(
                "mongodb://uptime:Basketball10@134.122.18.134:27017/Highpo_prod_copy?authSource=admin&w=1&readPreference=primary&appname=MongoDB%20Compass&directConnection=true&ssl=false"
            )
            db = client["Highpo_prod_copy"]
            video_collection = db["talents"]
            talent_id_object = ObjectId(talentId)

            video_collection.update_one(
                {"_id": talent_id_object},
                {
                    "$set": {
                        "language_ability_score": language_ability_score,
                        "fluency_score": fluency_score,
                        "confidence_level": confidence_label
                    }
                },
                upsert=True  # If the document doesn't exist, insert it
            )

            print("Scores saved successfully to MongoDB.")
        except Exception as e:
            print("Error:", e)

        return JsonResponse(response_data,safe=False)