"""Generate the default illustration for each sample food item (A2).

    python generate_images.py                     every item without a picture in seed_images/
    python generate_images.py --only seed-falafel one item (try the style first)
    python generate_images.py --force             regenerate all

Uses the image service in .env (IMAGE_GENERATOR=gemini needs GEMINI_API_KEY and
costs about $0.034 per picture). Commit seed_images/ afterwards, so the rest of
the group gets the pictures through `python seed.py` without paying again.
"""

import argparse
import sys

from app import create_app
from app.models.image_generation import (
    GeminiImageGenerator,
    ImageGenerationError,
    default_illustration_prompt,
)
from app.models.images import process_image
from seed import FOOD_ITEMS, SEED_IMAGES

PRICE_PER_IMAGE_USD = 0.034


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", action="append", metavar="ITEM_ID", help="only this item (can repeat)")
    parser.add_argument("--force", action="store_true", help="replace existing pictures")
    parser.add_argument("--yes", action="store_true", help="don't ask before calling a paid service")
    args = parser.parse_args()

    app = create_app()
    generator = app.extensions["image_generator"]
    if generator is None:
        print("Set IMAGE_GENERATOR=gemini (or fake) in .env first.", file=sys.stderr)
        return 1

    items = [i for i in FOOD_ITEMS if not args.only or i.id in args.only]
    unknown = set(args.only or []) - {i.id for i in items}
    if unknown:
        print(f"Unknown item ids: {', '.join(sorted(unknown))}", file=sys.stderr)
        return 1
    todo = [i for i in items if args.force or not (SEED_IMAGES / f"{i.id}.jpg").exists()]
    if not todo:
        print("All pictures exist. Use --force to regenerate.")
        return 0

    if isinstance(generator, GeminiImageGenerator) and not args.yes:
        cost = len(todo) * PRICE_PER_IMAGE_USD
        answer = input(f"Generate {len(todo)} pictures with {generator.model} (about ${cost:.2f})? [y/N] ")
        if answer.strip().lower() != "y":
            print("Aborted.")
            return 1

    SEED_IMAGES.mkdir(exist_ok=True)
    failed = 0
    for item in todo:
        print(f"{item.id}: generating…", end=" ", flush=True)
        try:
            data = process_image(generator.create(default_illustration_prompt(item)))
        except (ImageGenerationError, ValueError) as error:
            print(f"failed ({error})")
            failed += 1
            continue
        (SEED_IMAGES / f"{item.id}.jpg").write_bytes(data)
        print("saved")
    print("Done. Run `python seed.py` to use them, and commit seed_images/.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
