from rest_framework.pagination import PageNumberPagination
from .serializers import JwtResponseUserSerializer


# JWT 认证成功后，返回给用户的直，多加个 username
def jwt_response_payload_handler(token, user=None, request=None):
    return {
        'token': token,
        'username': JwtResponseUserSerializer(user).data.get('username')
    }


# 用户分页
class UserPagination(PageNumberPagination):
    page_size = 3
    page_size_query_param = 'page-size'
    page_query_param = "page"
    max_page_size = 100
