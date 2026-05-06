"""
URL configuration for DjangoProject project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path

from albaranes import views

urlpatterns = [
    path("", views.home, name="home"),

    # auth
    path(
        "login/",
        views.login_view,
        name="login"
    ),
    path(
        "logout/",
        views.logout_view,
        name="logout"
    ),
    path(
        "register/",
        views.register_view,
        name="register"
    ),

    # clients
    path(
        "clients/",
        views.clients_list,
        name="clients_list"
    ),
    path(
        "clients/nova/",
        views.client_create,
        name="client_create"
    ),
    path(
        "clients/<int:id>/",
        views.client_detail,
        name="client_detail"
    ),
    path(
        "clients/<int:id>/editar/",
        views.client_edit,
        name="client_edit"
    ),

    # cataleg
    path(
        "cataleg/",
        views.cataleg,
        name="cataleg"
    ),
    path(
        "cataleg/<str:categoria>/",
        views.cataleg_categoria,
        name="cataleg_categoria"
    ),

    # albarans
    path(
        "albarans/",
        views.albarans_list,
        name="albarans_list"
    ),
    path(
        "albarans/nova/",
        views.albara_create,
        name="albara_create"
    ),
    path(
        "albarans/<int:id>/",
        views.albara_detail,
        name="albara_detail"
    ),
    path(
        "albarans/<int:id>/afegir-linia/",
        views.linia_add,
        name="linia_add"    
    ),
    path(
        "albarans/<int:id>/estat/",
        views.albara_change_state,
        name="albara_change_state"
    ),

    # consulta
    path(
        "consulta/",
        views.consulta_form,
        name="consulta_form"
    ),
    path(
        "consulta/resultat/",
        views.consulta_result,
        name="consulta_resultat"
    ),

    # preparacio empleats
    path(
        "preparacio/",
        views.preparacio,
        name="preparacio"
    ),
    path(
        "preparacio/<int:id>/",
        views.preparacio_marcar_preparat,
        name="preparacio_marcar_preparat"
    ),

    # stock
    path(
        "stock/",
        views.stock_list,
        name="stock_list"
    ),
    path(
        "stock/reposicio/",
        views.stock_reposicio,
        name="stock_reposicio"
    ),

    # estadístiques
    path(
        "estadistiques/",
        views.estadistiques,
        name="estadistiques"
    ),
]


