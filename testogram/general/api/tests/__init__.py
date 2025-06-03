
from rest_framework.test import APITestCase
from rest_framework import status
from general.factories import (
    UserFactory,
    PostFactory,
    ReactionFactory,

)
from general.models import (
    Post,
    Reaction,
)
import json


class UserTestCase(APITestCase):
    def setUp(self):
        print("Запуск метода setUp")
        self.user = UserFactory()
        print(f"username: {self.user.username}\n")
        self.client.force_authenticate(user=self.user)
        self.url = "/api/users/"

    def test_user_list(self):
        UserFactory.create_batch(20)
        response = self.client.get(path=self.url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 10)
        self.assertEqual(response.data["count"], 21)

    def test_user_list_response_structure(self):
        response = self.client.get(path=self.url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

        expected_data = {
            "id": self.user.pk,
            "first_name": self.user.first_name,
            "last_name": self.user.last_name,
            "is_friend": False,
        }
        self.assertDictEqual(response.data["results"][0], expected_data)

    def test_user_list_is_friend_field(self):
        users = UserFactory.create_batch(5)

        self.user.friends.add(users[-1])
        self.user.save()

        with self.assertNumQueries(3):
            response = self.client.get(path=self.url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 6)

        self.assertTrue(response.data["results"][0]["is_friend"])

        for user_data in response.data["results"][1::]:
            self.assertFalse(user_data["is_friend"])

    def test_retrieve_user(self):
        target_user = UserFactory()

        # friends
        target_user.friends.add(self.user)
        target_user.friends.add(UserFactory())
        target_user.save()

        # posts
        post_1 = PostFactory(author=target_user, title="Post 1")
        post_2 = PostFactory(author=target_user, title="Post 2")

        # other posts
        PostFactory.create_batch(10)

        response = self.client.get(
            path=f"{self.url}{target_user.pk}/",
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_data = {
            "id": target_user.pk,
            "first_name": target_user.first_name,
            "last_name": target_user.last_name,
            "email": target_user.email,
            "is_friend": True,
            "friend_count": 2,
            "posts": [
                {
                    "id": post_1.pk,
                    "title": post_1.title,
                    "body": post_1.body,
                    "created_at": post_1.created_at.strftime("%Y-%m-%dT%H:%M:%S"),
                },
                {
                    "id": post_2.pk,
                    "title": post_2.title,
                    "body": post_2.body,
                    "created_at": post_2.created_at.strftime("%Y-%m-%dT%H:%M:%S"),
                },
            ],
        }
        self.assertDictEqual(expected_data, response.data)


    def test_get_user_friends(self):
        target_user = UserFactory()

        friends = UserFactory.create_batch(3)
        target_user.friends.set(friends)
        target_user.save()

        UserFactory.create_batch(5)

        url = f"{self.url}{target_user.pk}/friends/"
        response = self.client.get(path=url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 3)

        friend_ids = {user.pk for user in friends}
        for friend in response.data["results"]:
            self.assertTrue(friend["id"] in friend_ids)


    def test_get_user_friends_response_data_structure(self):
        target_user = UserFactory()

        friend = UserFactory()

        target_user.friends.add(friend)
        target_user.save()

        url = f"{self.url}{target_user.pk}/friends/"
        response = self.client.get(path=url, format="json")
        self.assertEqual(len(response.data["results"]), 1)

        expected_data = {
            "id": friend.pk,
            "first_name": friend.first_name,
            "last_name": friend.last_name,
            "is_friend": False,
        }
        self.assertDictEqual(response.data["results"][0], expected_data)

    def test_me(self):
        target_user = UserFactory()
        self.client.force_authenticate(user=target_user)

        # friends
        target_user.friends.add(self.user)
        target_user.friends.add(UserFactory())
        target_user.save()

        # posts
        post_1 = PostFactory(author=target_user, title="Post 1")
        post_2 = PostFactory(author=target_user, title="Post 2")

        # other posts
        PostFactory.create_batch(10)

        response = self.client.get(
            path=f"{self.url}me/",
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_data = {
            "id": target_user.pk,
            "first_name": target_user.first_name,
            "last_name": target_user.last_name,
            "email": target_user.email,
            "is_friend": False,
            "friend_count": 2,
            "posts": [
                {
                    "id": post_1.pk,
                    "title": post_1.title,
                    "body": post_1.body,
                    "created_at": post_1.created_at.strftime("%Y-%m-%dT%H:%M:%S"),
                },
                {
                    "id": post_2.pk,
                    "title": post_2.title,
                    "body": post_2.body,
                    "created_at": post_2.created_at.strftime("%Y-%m-%dT%H:%M:%S"),
                },
            ],
        }
        self.assertDictEqual(expected_data, response.data)


class PostTestCase(APITestCase):
    def setUp(self):
        self.user = UserFactory()
        self.client.force_authenticate(user=self.user)

        self.url = "/api/posts/"
    
    def test_create_post(self):
        data = {
            "title": "some post title",
            "body": "some text",
        }
        response = self.client.post(
            path=self.url,
            data=data,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        post = Post.objects.last()
        self.assertEqual(post.author, self.user)
        self.assertEqual(post.title, data["title"])
        self.assertEqual(post.body, data["body"])
        self.assertIsNotNone(post.created_at)

    def test_unauthorized_post_request(self):
        self.client.logout()

        data = {
            "title": "some post title",
            "body": "some text",
        }
        response = self.client.post(
            path=self.url,
            data=data,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(Post.objects.all().count(), 0)


    def test_post_list(self):
        PostFactory.create_batch(5)

        response = self.client.get(path=self.url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 5)


    def test_post_list_data_structure(self):
        post = PostFactory()
        response = self.client.get(path=self.url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        author = post.author
        expected_data = {
            "id": post.pk,
            "author": {
                "id": author.pk,
                "first_name": author.first_name,
                "last_name": author.last_name,
            },
            "title": post.title,
            "body": (
                post.body[:125] + "..."
                if len(post.body) > 128
                else post.body 
            ),
            "created_at": post.created_at.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        self.assertDictEqual(expected_data, response.data["results"][0])


    def test_retrieve_structure(self):
        post = PostFactory()
        author = post.author
        reaction = ReactionFactory(
            author=self.user,
            post=post,
            value=Reaction.Values.HEART,
        )

        response = self.client.get(
            path=f"{self.url}{post.pk}/",
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_data = {
            "id": post.pk,
            "author": {
                "id": author.pk,
                "first_name": author.first_name,
                "last_name": author.last_name,
            },
            "title": post.title,
            "body": post.body,
            "my_reaction": reaction.value,
            "created_at": post.created_at.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        self.assertDictEqual(expected_data, response.data)


    def test_retrieve_structure_without_own_reaction(self):
        post = PostFactory()

        response = self.client.get(
            path=f"{self.url}{post.pk}/",
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["my_reaction"], "")


    def test_update_own_post(self):
        post = PostFactory(
            author=self.user,
            title="old_title",
            body="old_body",
        )

        new_data = {
            "title": "new_title",
            "body": "new_body",
        }
        response = self.client.patch(
            path=f"{self.url}{post.pk}/",
            data=new_data,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.data["title"], new_data["title"])
        self.assertEqual(response.data["body"], new_data["body"])

        post.refresh_from_db()
        self.assertEqual(post.title, new_data["title"])
        self.assertEqual(post.body, new_data["body"])


    def test_try_to_update_other_post(self):
        post = PostFactory(
            title="old_title",
            body="old_body",
        )

        new_data = {
            "title": "new_title",
            "body": "new_body",
        }
        response = self.client.patch(
            path=f"{self.url}{post.pk}/",
            data=new_data,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    
    def test_update_own_post_with_put(self):
        post = PostFactory(
            author=self.user,
            title="old_title",
            body="old_body",
        )

        new_data = {
            "title": "new_title",
            "body": "new_body",
        }
        response = self.client.put(
            path=f"{self.url}{post.pk}/",
            data=new_data,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.data["title"], new_data["title"])
        self.assertEqual(response.data["body"], new_data["body"])

        post.refresh_from_db()
        self.assertEqual(post.title, new_data["title"])
        self.assertEqual(post.body, new_data["body"])

    
    def test_delete_post(self):
        post = PostFactory(
            author=self.user,
            title="old_title",
            body="old_body",
        )
        response = self.client.delete(
            path=f"{self.url}{post.pk}/",
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Post.objects.all().count(), 0)

    def test_try_to_delete_other_post(self):
        post = PostFactory(
            title="old_title",
            body="old_body",
        )
        response = self.client.delete(
            path=f"{self.url}{post.pk}/",
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)