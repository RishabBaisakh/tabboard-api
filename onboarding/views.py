from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from onboarding.serializers import OnboardingPatchSerializer
from onboarding.services import (
	get_onboarding_experience,
	get_onboarding_status,
	save_onboarding_step,
)


class OnboardingView(APIView):
	permission_classes = (IsAuthenticated,)

	def get(self, request):
		return Response(get_onboarding_experience(request.user))

	def patch(self, request):
		serializer = OnboardingPatchSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		result = save_onboarding_step(
			request.user,
			serializer.validated_data["step"],
			serializer.validated_data["data"],
		)
		return Response(result)


class OnboardingStatusView(APIView):
	permission_classes = (IsAuthenticated,)

	def get(self, request):
		return Response(get_onboarding_status(request.user))
