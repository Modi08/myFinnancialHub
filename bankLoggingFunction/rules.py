import re

RULES = [
    # Fixed Subscriptions
    (r"(?i)\b(spotify|netflix|apple|google\s*one|icloud|vodafone|kpn|odido|erasmus\s*sport|basic-fit|prime|disney|Metal plan fee|Primevideonl)\b", "Fixed - Subscriptions"),
    # Variable Subscriptions
    (r"(?i)\b(Google Cloud)\b", "Variable - Subscriptions"),
    # Groceries
    (r"(?i)\b(albert\s*heijn|ah\b|jumbo|dirk|lidl|aldi|ekoplaza|coop|mini[- ]mark[et]|super[- ]market)\b", "Food - Groceries"),
    # Dining
    (r"(?i)\b(mensa|koffie|starbucks|subway|thuisbezorgd|uber\s*eats|Bck\*has Doner Kebap O. Go|The Doner Company|Sumup  \*economische Fa|restaurant|Smullers|Bck*ns Automaat 3301|Essenza|Maydonoz Rotterdam Bv)\b", "Food - Dining Out"),
    # Campus
    (r"(?i)\b(spar\s*university|campus|erasmus\s*food|canteen|Has Doner Kebab Erasmu|Mozza Uni|Erasmus Spo)\b", "Food - Campus"),
    # Micro-mobility & Public Transit (including OVpay 'NLOV...' and NS ticket automats)
    (r"(?i)\b(check|felyx|bolt|tier|ns\s*groep|ret\b|gvb|arriva|nlov[a-z0-9]+|bck\*nsautomaat.*|nsautomaat|ov-chipkaart/Trans Link Systems|Lime\*[A-Za-z0-9 ]+|Umob)\b", "Transit / Incidental"),
    # Electronics & Tech Accessories
    (r"(?i)\b(coolblue|mediamarkt|bol\.com|bcc|anker|samsung)\b", "Electronics & Tech"),
    # Clothing & Apparel
    (r"(?i)\b(uniqlo|zara|h&m|asos|zalando|bershka|vintage|thrift|primark|Kapsalon)\b", "Clothing & Haircuts"),
    # Study Supplies & Stationery
    (r"(?i)\b(hema|bruna|studystore|action|staples|boeken|pen|paper)\b", "Study Supplies & Stationery"),
    # Nightlife & Social
    (r"(?i)\b(bar|caf[e ]|pub|bier|brewery|club|ticket|annabel|rotown|Avondmarkt De Dijk|Venue Maassilo B.v.|TicketingPayments|Ls Mick O Connells Rot|Carbonaro B.v.)\b", "Social & Nightlife"),
    # Investments
    (r"(?i)\b(Trading 212)\b", "Investments"),
    # Points Accumulation
    (r"^Ekansh Talwar$", "Revolut points"),
    #Savings Account
    (r"^To Instant Access Savings$", "Savings"),
    
    # ATM
    (r"^EKANSH SANDEEP TALWAR$", "ATM withdrawal"),
]

def classify_transaction(merchant: str, raw_amount: float, is_credit: bool) -> tuple[str, float, str]:
    """
    Evaluates transaction metadata against universal rules.
    Returns: (category, signed_amount, asset_note)
    """
    signed_amount = raw_amount if is_credit else -raw_amount

    # 1. Inflows / Top-ups / Reimbursements
    if is_credit:
        if re.search(r"(?i)\b(abn\s*amro|revolut\s*top[- ]?up)\b", merchant):
            return "Transfer - Internal", signed_amount, ""
        return "Reimbursement / Tikkie", signed_amount, ""

    elif raw_amount != 0:
        # 2. Categorize by Merchant Rules
        for pattern, category in RULES:
            if re.search(pattern, merchant):
                return category, signed_amount, ""
    else:
        return None, None, None

    return "General Discretionary", signed_amount, ""