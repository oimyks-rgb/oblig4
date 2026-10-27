import io

import pytest

from app.models.image_generation import FakeImageGenerator, ImageGenerationError, ImageGenerator
from app.models.images import image_name, process_image
from tests.conftest import make_item, picture_bytes


@pytest.fixture
def item(repositories):
    return repositories.food_items.add(make_item("soup", "Fish soup"))


def upload(client, data, item_id="soup"):
    return client.post(
        f"/admin/food-items/{item_id}/image/upload",
        data={"picture": (io.BytesIO(data), "photo.jpg")},
        content_type="multipart/form-data",
    )


def test_upload_preview_save(admin_client, repositories, item):
    response = upload(admin_client, picture_bytes((2000, 1500)))
    assert response.headers["Location"].endswith("/admin/food-items/soup/image/preview")

    preview = admin_client.get("/admin/food-items/soup/image/preview").get_data(as_text=True)
    assert "/images/draft-" in preview
    assert repositories.food_items.get("soup").image_filename is None  # not saved yet

    admin_client.post("/admin/food-items/soup/image/save")
    name = repositories.food_items.get("soup").image_filename
    assert name and not name.startswith("draft-")
    response = admin_client.get(f"/images/{name}")
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "image/jpeg"
    assert f"/images/{name}" in admin_client.get("/").get_data(as_text=True)


def test_saving_a_new_picture_deletes_the_old_one(admin_client, repositories, item):
    upload(admin_client, picture_bytes(color=(1, 2, 3)))
    admin_client.post("/admin/food-items/soup/image/save")
    first = repositories.food_items.get("soup").image_filename

    upload(admin_client, picture_bytes(color=(250, 250, 0)))
    admin_client.post("/admin/food-items/soup/image/save")
    assert repositories.food_items.get("soup").image_filename != first
    assert not repositories.images.exists(first)


def test_discard_keeps_current_picture(admin_client, repositories, item):
    upload(admin_client, picture_bytes())
    draft = admin_client.get("/admin/food-items/soup/image/preview").get_data(as_text=True).split("/images/")[-1].split('"')[0]
    admin_client.post("/admin/food-items/soup/image/discard")
    assert not repositories.images.exists(draft)
    assert repositories.food_items.get("soup").image_filename is None
    # preview without a draft goes back to the picture page
    assert admin_client.get("/admin/food-items/soup/image/preview").status_code == 302


def test_remove_picture(admin_client, repositories, item):
    upload(admin_client, picture_bytes())
    admin_client.post("/admin/food-items/soup/image/save")
    name = repositories.food_items.get("soup").image_filename
    admin_client.post("/admin/food-items/soup/image/remove")
    assert repositories.food_items.get("soup").image_filename is None
    assert not repositories.images.exists(name)


def test_picture_shared_by_two_items_is_kept(admin_client, repositories, item):
    data = process_image(picture_bytes())
    name = repositories.images.save(data)
    repositories.food_items.add(make_item("cake", "Cake", image_filename=name))
    repositories.food_items.update(make_item("soup", "Fish soup", image_filename=name))
    admin_client.post("/admin/food-items/soup/image/remove")
    assert repositories.images.exists(name)


def test_invalid_upload_shows_error(admin_client, item):
    response = upload(admin_client, b"not a picture")
    assert response.status_code == 400
    assert "not a picture" in response.get_data(as_text=True)


def test_ai_options_hidden_when_no_generator(admin_client, item):
    html = admin_client.get("/admin/food-items/soup/image").get_data(as_text=True)
    assert "Upload a picture" in html
    assert "Create or modify with AI" not in html
    assert admin_client.post("/admin/food-items/soup/image/generate", data={"instruction": "x"}).status_code == 404


@pytest.fixture
def with_fake_generator(app):
    app.extensions["image_generator"] = FakeImageGenerator()


def test_generate_create_and_modify(admin_client, repositories, item, with_fake_generator):
    html = admin_client.get("/admin/food-items/soup/image").get_data(as_text=True)
    assert "Create or modify with AI" in html
    assert "flat vector illustration of Fish soup" in html  # suggested prompt

    response = admin_client.post("/admin/food-items/soup/image/generate", data={"mode": "create", "instruction": "Soup"})
    assert response.headers["Location"].endswith("/image/preview")
    admin_client.post("/admin/food-items/soup/image/save")
    first = repositories.food_items.get("soup").image_filename

    response = admin_client.post("/admin/food-items/soup/image/generate", data={"mode": "modify", "instruction": "Add dill"})
    assert response.headers["Location"].endswith("/image/preview")
    admin_client.post("/admin/food-items/soup/image/save")
    assert repositories.food_items.get("soup").image_filename != first


def test_generate_validation(admin_client, item, with_fake_generator):
    post = lambda **data: admin_client.post("/admin/food-items/soup/image/generate", data=data)
    assert post(mode="create", instruction=" ").status_code == 400
    assert post(mode="create", instruction="x" * 1001).status_code == 400
    assert post(mode="modify", instruction="Add dill").status_code == 400  # no picture yet


def test_generator_failure_is_shown(admin_client, app, item):
    class Broken(ImageGenerator):
        def create(self, instruction):
            raise ImageGenerationError("The image service failed: quota exceeded")

        def modify(self, image, instruction):
            raise NotImplementedError

    app.extensions["image_generator"] = Broken()
    response = admin_client.post("/admin/food-items/soup/image/generate", data={"mode": "create", "instruction": "Soup"})
    assert response.status_code == 502
    assert "quota exceeded" in response.get_data(as_text=True)


def test_new_item_goes_to_picture_page(admin_client):
    response = admin_client.post("/admin/food-items/new", data={"name": "Cake", "price_nok": "10", "min_order_qty": "1"})
    assert "/image" in response.headers["Location"]


def test_customer_cannot_manage_pictures(customer_client, item):
    assert customer_client.get("/admin/food-items/soup/image").status_code == 403
    assert upload(customer_client, picture_bytes()).status_code == 403


def test_image_route_rejects_unknown_and_unsafe_names(client, repositories):
    assert client.get("/images/" + "a" * 32 + ".jpg").status_code == 404
    assert client.get("/images/..%2Fconfig.py").status_code == 404
    assert client.get("/images/x.jpg").status_code == 404


def test_drafts_are_not_public(client, repositories):
    draft = repositories.images.save(process_image(picture_bytes()), draft=True)
    assert client.get(f"/images/{draft}").status_code == 404


def test_too_large_upload_is_refused(admin_client, app, item):
    app.config["MAX_CONTENT_LENGTH"] = 1000
    response = upload(admin_client, b"x" * 5000)
    assert response.status_code == 302
