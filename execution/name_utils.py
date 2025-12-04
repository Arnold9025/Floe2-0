def normalize_name(firstname, lastname, email):
    """
    Returns a clean, human-friendly name with fallbacks.
    """
    # Clean inputs
    firstname = firstname.strip() if firstname else ""
    lastname = lastname.strip() if lastname else ""
    email = email.strip() if email else ""

    # 1. If both exist
    if firstname and lastname:
        return f"{firstname} {lastname}"
    
    # 2. If only one exists
    if firstname:
        return firstname
    if lastname:
        return lastname
    
    # 3. Fallback to Email Prefix
    if email and '@' in email:
        prefix = email.split('@')[0]
        # Remove numbers or special chars if you want, but simple capitalization is a good start
        # e.g. arnold.adadjisso -> Arnold Adadjisso
        clean_prefix = prefix.replace('.', ' ').replace('_', ' ').replace('-', ' ')
        return clean_prefix.title()
    
    # 4. Ultimate Fallback
    return "Prospect"
