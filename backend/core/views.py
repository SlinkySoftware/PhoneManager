"""REST API viewsets for core resources."""
from django.contrib.auth.models import User
from rest_framework import permissions, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import Device, DeviceTypeConfig, Line, SIPServer, Site
from .serializers import DeviceSerializer, DeviceTypeConfigSerializer, LineSerializer, SIPServerSerializer, SiteSerializer


class AdminOrReadOnly(permissions.BasePermission):
    """Allow read for all authenticated users; write for staff."""

    def has_permission(self, request, view) -> bool:
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return bool(request.user and request.user.is_staff)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login(request):
    """Authenticate user and return token."""
    username = request.data.get('username')
    password = request.data.get('password')

    if not username or not password:
        return Response(
            {'detail': 'Username and password required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return Response(
            {'detail': 'Invalid username or password'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    if not user.check_password(password):
        return Response(
            {'detail': 'Invalid username or password'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    # Get or create token
    token, _ = Token.objects.get_or_create(user=user)

    return Response({
        'token': token.key,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_staff': user.is_staff
        }
    }, status=status.HTTP_200_OK)


class SIPServerViewSet(viewsets.ModelViewSet):
    queryset = SIPServer.objects.all()
    serializer_class = SIPServerSerializer
    permission_classes = [AdminOrReadOnly]


class SiteViewSet(viewsets.ModelViewSet):
    queryset = Site.objects.select_related("primary_sip_server", "secondary_sip_server")
    serializer_class = SiteSerializer
    permission_classes = [AdminOrReadOnly]


class LineViewSet(viewsets.ModelViewSet):
    queryset = Line.objects.all()
    serializer_class = LineSerializer
    permission_classes = [AdminOrReadOnly]


class DeviceViewSet(viewsets.ModelViewSet):
    queryset = Device.objects.select_related("site", "line_1")
    serializer_class = DeviceSerializer
    permission_classes = [AdminOrReadOnly]


class DeviceTypeConfigViewSet(viewsets.ModelViewSet):
    queryset = DeviceTypeConfig.objects.all()
    serializer_class = DeviceTypeConfigSerializer
    permission_classes = [AdminOrReadOnly]
