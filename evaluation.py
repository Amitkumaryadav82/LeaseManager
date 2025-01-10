from getLeaseInfo import getLeaseInfo
# import evaluate
from rouge import Rouge
from sacrebleu.metrics import BLEU
from nltk.translate.bleu_score import sentence_bleu
import numpy as np


def getEvalMetrics():
    rouge_scorer = Rouge()

    query = [
        "for the lease agreement with M.A.S. REAL ESTATE SERVICES LTD., what is the notice period for termination of lease",
        "What is the approved Tenant Improvement Budget for the lease with High Range SV1 LLC for the property in Scottsdale, Arizona",
        "For Lease GS-09B-02614, where do I need to submit the invoices?"
    ]

    response = [
        "As per lease GS-09B-02625, lease can be terminated in partial or whole anytime after 10th year from the day of commencement by providing 90 days notice to Lessor",
        "As per lease GS-09B-02614, the Tenant Improvement Budget is $1,311,799.00",
        "As per lease GS-09B-002614, invoices should be submitted at: GSA Office Of Finance, P.O. Box 17181, Fort Worth, TX-760102-0181"
    ]

    total_rouge_score = 0
    total_bleu_score = 0

    for i in range(3):
        rouge_score = rouge_scorer.get_scores(query[i], response[i])
        total_rouge_score += rouge_score[0]["rouge-l"]["f"]
        bleu_score = sentence_bleu([response[i].split()], query[i].split())
        total_bleu_score += bleu_score

    avg_rouge = total_rouge_score / 3
    avg_bleu = total_bleu_score / 3

    print("** Rouge: ", avg_rouge)
    print("** BLEU: ", avg_bleu)

    return avg_bleu, avg_rouge

if __name__ == '__main__':
    avg_bleu, avg_rouge = getEvalMetrics()
    print("**Avg BLEU: ", avg_bleu)
    print("**Avg ROUGE: ", avg_rouge)
