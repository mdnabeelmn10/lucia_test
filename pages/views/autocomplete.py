# import os
# import openai
# from django.conf import settings
# from rest_framework.decorators import api_view, permission_classes
# from rest_framework.permissions import IsAuthenticated  # replace with your custom permissions
# from rest_framework.response import Response
# from rest_framework import status

# from ..permissions import IsDonorAdvisor, IsLuciaAdmin
# from ..serializers import CharityVerificationSerializer

# openai.api_key = os.getenv("OPENAI_API_KEY")
# def get_charity_info_with_openai(charity_name: str):
#     """
#     Given a charity name, use OpenAI to return structured info in JSON.
#     """
#     prompt = f"""
#     You are an expert assistant. I will give you the full name of a US charity.
#     Provide the following information in strict JSON format:

#     - charity_name
#     - address
#     - contact_email
#     - contact_phone
#     - website
#     - tin (EIN)
#     - is_tax_exempt_revoked (true/false if known, otherwise null)

#     If any information is unavailable, return null for that field.

#     Charity Name: "{charity_name}"
#     """

#     try:
#         response = openai.ChatCompletion.create(
#             model="gpt-4o-mini",
#             messages=[
#                 {"role": "system", "content": "You are a JSON extractor for US charities."},
#                 {"role": "user", "content": prompt},
#             ],
#             temperature=0,
#         )

#         content = response["choices"][0]["message"]["content"]

#         import json
#         data = json.loads(content)
#         print(data)

#         # Map OpenAI keys to serializer keys
#         if "charity_name" in data:
#             data["name"] = data.pop("charity_name")
#         if "contact_email" in data:
#             data["contactEmail"] = data.pop("contact_email")
#         if "contact_phone" in data:
#             data["contactTelephone"] = data.pop("contact_phone")
#         if "is_tax_exempt_revoked" in data:
#             data["irs_revoked"] = data.pop("is_tax_exempt_revoked")
#         if "source" not in data:
#             data["source"] = ["openai"]
#         else:
#             data["source"].append("openai")
#         return data

#     except Exception as e:
#         return {"error": f"OpenAI extraction failed: {e}", "source": []}


# # ---- DRF Endpoint ----
# @api_view(['GET'])
# @permission_classes([IsDonorAdvisor | IsLuciaAdmin])
# def verify_charity(request):
#     """
#     Endpoint: /verify-charity?name=<full_charity_name>
#     Returns structured charity info using OpenAI.
#     """
#     charity_name = request.GET.get("name")
#     if not charity_name:
#         return Response({"error": "Missing charity name"}, status=status.HTTP_400_BAD_REQUEST)

#     result = get_charity_info_with_openai(charity_name)
#     print(result)
#     serializer = CharityVerificationSerializer(result)
#     return Response(serializer.data, status=status.HTTP_200_OK)


import os
import json
import openai
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated  # replace with your custom permissions
from rest_framework.response import Response
from rest_framework import status

from ..permissions import IsDonorAdvisor, IsLuciaAdmin
from ..serializers import CharityVerificationSerializer

openai.api_key = os.getenv("OPENAI_API_KEY")


def get_charity_info_with_openai(charity_name: str):
    """
    Given a charity name, use OpenAI to return structured info in JSON.
    """
    prompt = f"""
    You are an expert assistant. I will give you the full name of a US charity.
    Provide the following information in strict JSON format:
    - charity_name
    - address
    - contact_name
    - contact_email
    - contact_phone
    - website
    - tin (EIN)
    - is_tax_exempt_revoked (true/false if known, otherwise null)

    If any information is unavailable, return null for that field.
    Charity Name: "{charity_name}"
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a JSON extractor for US charities."},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
        )

        content = response["choices"][0]["message"]["content"]

        # Try to extract only JSON portion
        try:
            data = json.loads(content)
        except Exception:
            import re
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match:
                data = json.loads(match.group())
            else:
                raise

        # Map to serializer + frontend fields
        mapped = {
            "name": data.get("charity_name"),
            "tin": data.get("tin"),
            "address": data.get("address"),
            "website": data.get("website"),
            "contactName": data.get("contact_name"),
            "contactEmail": data.get("contact_email"),
            "contactTelephone": data.get("contact_phone"),
            "irs_revoked": data.get("is_tax_exempt_revoked"),
            "source": ["openai"],
        }

        return mapped

    except Exception as e:
        return {"error": f"OpenAI extraction failed: {e}", "source": []}


# ---- DRF Endpoint ----
@api_view(['GET'])
@permission_classes([IsDonorAdvisor | IsLuciaAdmin])
def verify_charity(request):
    """
    Endpoint: /verify-charity?name=<full_charity_name>
    Returns structured charity info using OpenAI.
    """
    charity_name = request.GET.get("name")
    if not charity_name:
        return Response({"error": "Missing charity name"}, status=status.HTTP_400_BAD_REQUEST)

    result = get_charity_info_with_openai(charity_name)
    serializer = CharityVerificationSerializer(result)
    return Response(serializer.data, status=status.HTTP_200_OK)
