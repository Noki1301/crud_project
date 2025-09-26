from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model


User = get_user_model()


class UserViewTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="adminpass",
            first_name="Admin",
            last_name="User",
            is_staff=True,
        )
        self.user = User.objects.create_user(
            username="janedoe",
            email="jane@example.com",
            password="secret123",
            first_name="Jane",
            last_name="Doe",
            is_active=True,
        )
        session = self.client.session
        session["dashboard_user_id"] = self.staff.pk
        session.save()

    def test_user_list_filters_and_pagination(self):
        extra_users = [
            User(
                username=f"user{i}",
                email=f"user{i}@example.com",
                first_name="User",
                last_name=str(i),
                is_active=i % 2 == 0,
            )
            for i in range(20)
        ]
        User.objects.bulk_create(extra_users)

        url = reverse("dashboard:user_list")

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["is_paginated"])  # paginate_by = 10

        response_page_two = self.client.get(url, {"page": 2})
        self.assertEqual(response_page_two.status_code, 200)
        self.assertIn("users", response_page_two.context)

        response_search = self.client.get(url, {"q": "janedoe"})
        self.assertContains(response_search, "janedoe")
        self.assertNotContains(response_search, "user1")

        response_inactive = self.client.get(url, {"status": "inactive"})
        for item in response_inactive.context["users"]:
            self.assertFalse(item.is_active)

    def test_create_user_success_message(self):
        response = self.client.post(
            reverse("dashboard:user_create"),
            {
                "username": "newuser",
                "email": "newuser@example.com",
                "first_name": "New",
                "last_name": "User",
                "is_active": True,
                "is_staff": False,
            },
            follow=True,
        )
        self.assertRedirects(response, reverse("dashboard:user_list"))
        self.assertTrue(User.objects.filter(username="newuser").exists())
        messages = list(response.context["messages"])
        self.assertTrue(any("created successfully" in str(message) for message in messages))

    def test_update_user_success_message(self):
        response = self.client.post(
            reverse("dashboard:user_update", args=[self.user.pk]),
            {
                "username": "janedoe",
                "email": "jane@example.com",
                "first_name": "Janet",
                "last_name": "Doe",
                "is_active": True,
                "is_staff": False,
            },
            follow=True,
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Janet")
        messages = list(response.context["messages"])
        self.assertTrue(any("updated successfully" in str(message) for message in messages))

    def test_delete_user_via_post(self):
        response = self.client.post(reverse("dashboard:user_delete", args=[self.user.pk]), follow=True)
        self.assertRedirects(response, reverse("dashboard:user_list"))
        self.assertFalse(User.objects.filter(pk=self.user.pk).exists())
        messages = list(response.context["messages"])
        self.assertTrue(any("deleted successfully" in str(message) for message in messages))
