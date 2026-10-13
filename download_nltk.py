import nltk
import ssl

try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

resources = ['punkt', 'punkt_tab', 'stopwords', 'wordnet', 'averaged_perceptron_tagger', 'omw-1.4']

for r in resources:
    print(f"Downloading {r}...")
    result = nltk.download(r, quiet=False)
    print(f"  -> {'OK' if result else 'Already exists or failed'}")

print("\nAll NLTK data downloaded successfully!")
