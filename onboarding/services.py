from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from onboarding.models import OnboardingOption, OnboardingQuestion, OnboardingResponse
from users.models import Interest, PersonalityTag, UserProfile
from users.services import update_user_profile


def get_user_profile(user):
    profile = UserProfile.objects.filter(user=user).first()
    if profile is None:
        raise NotFound("User profile is unavailable. Please sign in again.")
    return profile


def get_onboarding_status(user):
    profile = get_user_profile(user)
    return {"is_complete": profile.onboarding_completed_at is not None}


def get_onboarding_experience(user):
    profile = get_user_profile(user)
    questions = OnboardingQuestion.objects.filter(is_active=True).prefetch_related(
        "options"
    )
    response_map = {
        response.question_id: [
            option.pk for option in response.selected_options.filter(is_active=True)
        ]
        for response in OnboardingResponse.objects.filter(user=user).prefetch_related(
            "selected_options"
        )
    }

    question_data = []
    for question in questions:
        question_data.append(
            {
                "id": question.pk,
                "key": question.key,
                "text": question.text,
                "selection_type": question.selection_type,
                "max_selections": question.max_selections,
                "is_required": question.is_required,
                "options": [
                    {"id": option.pk, "key": option.key, "label": option.label}
                    for option in question.options.all()
                    if option.is_active
                ],
                "selected_option_ids": response_map.get(question.pk, []),
            }
        )

    return {
        "is_complete": profile.onboarding_completed_at is not None,
        "onboarding_completed_at": profile.onboarding_completed_at,
        "profile": {
            "display_name": profile.display_name,
            "bio": profile.bio,
            "time_zone": profile.time_zone,
        },
        "basic_info": {"questions": question_data},
        "interests": {
            "options": [
                {"id": item.pk, "key": item.key, "name": item.name}
                for item in Interest.objects.filter(is_active=True)
            ],
            "selected_ids": list(
                profile.interests.filter(is_active=True).values_list("id", flat=True)
            ),
        },
        "personality_tags": {
            "options": [
                {"id": item.pk, "key": item.key, "name": item.name}
                for item in PersonalityTag.objects.filter(is_active=True)
            ],
            "selected_ids": list(
                profile.personality_tags.filter(is_active=True).values_list(
                    "id", flat=True
                )
            ),
        },
    }


def _get_question(answer):
    questions = OnboardingQuestion.objects.filter(is_active=True)
    if "question_key" in answer:
        question = questions.filter(key=answer["question_key"]).first()
    else:
        question = questions.filter(pk=answer["question_id"]).first()
    if question is None:
        raise ValidationError(
            {"answers": "One or more questions do not exist or are inactive."}
        )
    return question


def _save_answer(user, answer, question=None):
    question = question or _get_question(answer)
    option_ids = answer["selected_option_ids"]

    selection_limit = min(question.max_selections, 3)
    if len(option_ids) > selection_limit:
        raise ValidationError(
            {
                "answers": {
                    question.key: f"Select no more than {selection_limit} options."
                }
            }
        )
    if (
        question.selection_type == OnboardingQuestion.SelectionType.SINGLE
        and len(option_ids) > 1
    ):
        raise ValidationError({"answers": {question.key: "Select exactly one option."}})
    if question.is_required and not option_ids:
        raise ValidationError(
            {"answers": {question.key: "This question requires an answer."}}
        )

    options = list(
        OnboardingOption.objects.filter(
            question=question,
            is_active=True,
            pk__in=option_ids,
        )
    )
    if len(options) != len(option_ids):
        raise ValidationError(
            {
                "answers": {
                    question.key: "Every selected option must be active and belong to this question."
                }
            }
        )

    response, _ = OnboardingResponse.objects.get_or_create(
        user=user,
        question=question,
    )
    response.selected_options.set(options)
    response.save(update_fields=["updated_at"])
    return {
        "question_key": question.key,
        "selected_option_ids": [option.pk for option in options],
    }


def _save_answers(user, answers):
    saved_answers = []
    seen_question_ids = set()
    for answer in answers:
        question = _get_question(answer)
        if question.pk in seen_question_ids:
            raise ValidationError(
                {"answers": "A question may only be submitted once per request."}
            )
        seen_question_ids.add(question.pk)
        saved_answers.append(_save_answer(user, answer, question))
    return saved_answers


def _resolve_active_options(model, option_ids, field_name):
    options = list(model.objects.filter(is_active=True, pk__in=option_ids))
    if len(options) != len(option_ids):
        raise ValidationError(
            {field_name: "Every selected item must exist and be active."}
        )
    return options


def _maybe_complete_onboarding(profile):
    if profile.onboarding_completed_at is not None:
        return

    required_questions = OnboardingQuestion.objects.filter(
        is_active=True,
        is_required=True,
    )
    responses = {
        response.question_id: response
        for response in OnboardingResponse.objects.filter(
            user=profile.user,
            question__in=required_questions,
        ).prefetch_related("selected_options")
    }
    for question in required_questions:
        response = responses.get(question.pk)
        if response is None:
            return
        options = list(response.selected_options.all())
        if not options or len(options) > question.max_selections:
            return
        if (
            question.selection_type == OnboardingQuestion.SelectionType.SINGLE
            and len(options) != 1
        ):
            return
        if any(
            not option.is_active or option.question_id != question.pk
            for option in options
        ):
            return

    if not profile.interests.filter(is_active=True).exists():
        return
    if not profile.personality_tags.filter(is_active=True).exists():
        return

    profile.onboarding_completed_at = timezone.now()
    profile.save(update_fields=["onboarding_completed_at", "updated_at"])


@transaction.atomic
def save_onboarding_step(user, step, data):
    profile = UserProfile.objects.select_for_update().filter(user=user).first()
    if profile is None:
        raise NotFound("User profile is unavailable. Please sign in again.")

    if step == "basic_info":
        profile = update_user_profile(
            profile,
            {
                field: data[field]
                for field in ("display_name", "bio", "time_zone")
                if field in data
            },
        )
        saved = {
            "profile": {
                "display_name": profile.display_name,
                "bio": profile.bio,
                "time_zone": profile.time_zone,
            },
        }
    elif step == "questions":
        saved = {"answers": _save_answers(user, data["answers"])}
    elif step == "interests":
        options = _resolve_active_options(
            Interest,
            data["selected_ids"],
            "selected_ids",
        )
        update_user_profile(profile, {"interests": options})
        saved = {"selected_ids": [item.pk for item in options]}
    else:
        options = _resolve_active_options(
            PersonalityTag,
            data["selected_ids"],
            "selected_ids",
        )
        update_user_profile(profile, {"personality_tags": options})
        saved = {"selected_ids": [item.pk for item in options]}

    _maybe_complete_onboarding(profile)
    profile.refresh_from_db(fields=["onboarding_completed_at"])
    return {
        "step": step,
        "saved": saved,
        "is_complete": profile.onboarding_completed_at is not None,
        "onboarding_completed_at": profile.onboarding_completed_at,
    }
