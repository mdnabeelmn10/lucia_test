from .models import VoteType
from .models import UserRole
from .models import User

def is_majority_approved(donation):
    """
    Returns True if majority of total directors have approved the donation,
    else False.
    Abstain/More Info votes don't count.
    """
    votes = list(donation.votes.values_list('vote', flat=True))

    approve = votes.count(VoteType.APPROVE)
    disapprove = votes.count(VoteType.DISAPPROVE)

    total_directors = User.objects.filter(role=UserRole.LUCIA_DIRECTOR).count()

    if total_directors == 0:
        return False  # safety

    majority_needed = total_directors // 2 + 1

    return approve >= majority_needed
