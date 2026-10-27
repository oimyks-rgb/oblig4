from app.models.images import image_name, process_image
from seed import FOOD_ITEMS, attach_seed_images
from tests.conftest import picture_bytes


def test_seed_pictures_are_attached_with_content_hash_names(repositories, tmp_path):
    item = FOOD_ITEMS[0]
    repositories.food_items.add(item)
    data = process_image(picture_bytes())
    (tmp_path / f"{item.id}.jpg").write_bytes(data)

    assert attach_seed_images(repositories, tmp_path) == 1
    assert repositories.food_items.get(item.id).image_filename == image_name(data)
    assert repositories.images.read(image_name(data)) == data

    assert attach_seed_images(repositories, tmp_path) == 0  # nothing to do on rerun


def test_missing_local_file_is_restored(repositories, tmp_path):
    """Another member attached the picture: the database has the name, this machine lacks the file."""
    item = FOOD_ITEMS[0]
    data = process_image(picture_bytes())
    repositories.food_items.add(item.__class__(**{**item.__dict__, "image_filename": image_name(data)}))
    (tmp_path / f"{item.id}.jpg").write_bytes(data)

    assert attach_seed_images(repositories, tmp_path) == 1
    assert repositories.images.exists(image_name(data))


def test_staff_pictures_are_not_replaced(repositories, tmp_path):
    item = FOOD_ITEMS[0]
    staff_name = repositories.images.save(process_image(picture_bytes(color=(9, 9, 9))))
    repositories.food_items.add(item.__class__(**{**item.__dict__, "image_filename": staff_name}))
    (tmp_path / f"{item.id}.jpg").write_bytes(process_image(picture_bytes()))

    assert attach_seed_images(repositories, tmp_path) == 0
    assert repositories.food_items.get(item.id).image_filename == staff_name
