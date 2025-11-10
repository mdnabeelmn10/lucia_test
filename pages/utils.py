# donations/utils.py

from .models import VoteType

def get_majority_decision(donation):
    """
    Compute the majority vote for display.
    Always returns a string (never NaN/None).
    """
    votes = list(donation.votes.values_list('vote', flat=True))

    approve = votes.count(VoteType.APPROVE)
    disapprove = votes.count(VoteType.DISAPPROVE)
    abstain = votes.count(VoteType.ABSTAIN)
    more_info = votes.count(VoteType.MORE_INFO)

    total_votes = len(votes)
    if total_votes == 0:
        return "No votes yet"

    if approve > disapprove:
        return "Majority Approve"
    elif disapprove > approve:
        return "Majority Disapprove"
    else:
        return "Tie"
