# -*- coding: utf-8 -*-
from datetime import datetime
from rest_framework.response import Response
from rest_framework.views import APIView
from api.packages.response import Response as response
from api.project.models import *
from api.project.serializers import *
from api.packages.globalfunction import *
from rest_framework.authentication import TokenAuthentication
from oauth2_provider.contrib.rest_framework import *
from django.conf import settings
from django.core.cache.backends.base import DEFAULT_TIMEOUT
CACHE_TTL = getattr(settings, 'CACHE_TTL', DEFAULT_TIMEOUT)
from api.packages.multiupload import *
from api.packages.common import *
from api.packages.constants import *
from django.db.models import Prefetch
from django.db import transaction
from django.db.models import Q, CharField, Value as V
from django.db.models.functions import Concat
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

class ProjectListingApiView(APIView):
    """
    Project listing
    """
    authentication_classes = [OAuth2Authentication]

    @staticmethod
    def post(request):
        try:
            data = request.data
            offset = 0
            if 'page_size' in data and data['page_size'] != "":
                limit = int(data['page_size'])
            else:
                limit = int(settings.LIST_PER_PAGE)

            if 'page' in data and data['page'] != "":
                page = int(data['page'])
            else:
                page = 1
            # -----------Set Pagination Value--------
            if limit > 0:
                offset = (page - 1) * limit
                limit = limit * page

            if "site_id" in data and data['site_id'] != "":
                site_id = int(data['site_id'])
                network = NetworkDomain.objects.filter(id=site_id, is_active=1).first()
                if network is None:
                    return Response(response.parsejson("Site not exist.", "", status=403))
            else:
                return Response(response.parsejson("site_id is required", "", status=403))
            user_domain = None
            is_developer = None
            if "user_id" in data and data['user_id'] != "":
                user_id = int(data['user_id'])
                users = Users.objects.filter(id=user_id, site=site_id, user_type=2, status=1).first()
                is_agent = None
                if users is None:
                    is_agent = True
                    users = Users.objects.filter(id=user_id, user_type=2, status=1).first()
                    if users is None:
                        users = Users.objects.filter(id=user_id, network_user__domain=site_id, network_user__is_agent=1, network_user__status=1, status=1, user_type=4).first()
                        if users is None:
                            return Response(response.parsejson("User not exist.", "", status=403))
                data["agent"] = user_id
                user_domain = users.site_id
            else:
                return Response(response.parsejson("user_id is required.", "", status=403))
            project_listing = DeveloperProject.objects.filter(domain=site_id).exclude(project_status=5)
            if is_agent is not None:
                project_listing = project_listing.filter(agent=user_id)

            # -----------------Filter-------------------
            if "developer_id" in data and data["developer_id"] != "":
                developer_id = int(data["developer_id"])
                project_listing = project_listing.filter(Q(agent=developer_id))

            if "status" in data and data["status"] != "":
                status = int(data["status"])
                project_listing = project_listing.filter(Q(project_status=status))

            if "project_status" in data and data["project_status"] != "":
                project_status = int(data["project_status"])
                project_listing = project_listing.filter(Q(status=project_status))

            if "project_type" in data and data["project_type"] != "":
                project_type = int(data["project_type"])
                project_listing = project_listing.filter(Q(developer_project_type__project_type=project_type))

            # -----------------Search-------------------
            if 'search' in data and data['search'] != "":
                search = data['search'].strip()
                # project_listing = project_listing.annotate(project_name=Concat('address_one', V(', '), 'city', V(', '), 'state__state_name', V(' '), 'postal_code', output_field=CharField())).annotate(full_name=Concat('agent__user_business_profile__first_name', V(' '), 'agent__user_business_profile__last_name')).filter(Q(property_asset__name__icontains=search) | Q(sale_by_type__auction_type__icontains=search) | Q(agent__user_business_profile__company_name__icontains=search) | Q(full_name__icontains=search) | Q(city__icontains=search) | Q(address_one__icontains=search) | Q(state__state_name__icontains=search) | Q(property_type__property_type__icontains=search) | Q(property_name__icontains=search) | Q(postal_code__icontains=search))
                project_listing = DeveloperProject.objects.filter(domain=site_id).exclude(project_status=5)
                project_listing = project_listing.annotate(
                    annotated_project_name=Concat(
                        'address_one',
                        V(', '),
                        'city__state_name',
                        V(', '),
                        'country__country_name',
                        output_field=CharField()
                    )
                ).filter(
                    Q(project_name__icontains=search) |
                    Q(annotated_project_name__icontains=search) |
                    Q(agent__user_business_profile__company_name__icontains=search) |
                    Q(city__state_name__icontains=search) |
                    Q(address_one__icontains=search) |
                    Q(country__country_name__icontains=search) |
                    Q(neighborhood__icontains=search) |
                    Q(community__icontains=search) |
                    Q(postal_code__icontains=search)
                )

            total = project_listing.count()
            project_listing = project_listing.order_by(F("ordering").asc(nulls_last=True)).only("id")[offset:limit]
            serializer = ProjectListingSerializer(project_listing, many=True)
            all_data = {"data": serializer.data, "total": total, "user_domain": user_domain}
            return Response(response.parsejson("Fetch Data.", all_data, status=201))
        except Exception as exp:
            return Response(response.parsejson(str(exp), exp, status=403))

class ProjectTypeApiView(APIView):
    """ This is ProjectTypeApiView class

    """
    authentication_classes = [TokenAuthentication, OAuth2Authentication]

    def post(self, request):
        try:
            project_type = LookupDeveloperProjectType.objects
            project_type = project_type.filter(is_active=1)

            project_type = project_type.order_by("-id").values("id", "name")
            return Response(response.parsejson("Fetch data", project_type, status=201))
        except Exception as exp:
            return Response(response.parsejson("Unable to process", "", status=403))

class FacilityListApiView(APIView):
    """ This is FacilityListApiView class

    """
    authentication_classes = [TokenAuthentication, OAuth2Authentication]

    def post(self, request):
        try:
            project_facilities = DeveloperProjectFacility.objects.select_related('upload').filter(is_active=True).order_by("-id")
            serializer = DeveloperProjectFacilitySerializer(project_facilities, many=True)

            return Response(response.parsejson("Fetch data", serializer.data, status=201))
        except Exception as exp:
            print(exp)
            return Response(response.parsejson("Unable to process", "", status=403))

class ProjectStatusListApiView(APIView):
    """ This is ProjectStatusListApiView class

    """
    authentication_classes = [TokenAuthentication, OAuth2Authentication]

    def get(self, request):
        try:
            property_status_list = LookupDeveloperProjectStatus.objects
            property_status_list = property_status_list.filter(is_active=1)

            property_status_list = property_status_list.order_by("id").values("id", "status_name")
            return Response(response.parsejson("Fetch data", property_status_list, status=201))
        except Exception as exp:
            return Response(response.parsejson("Unable to process", "", status=403))

class AddDeveloperProjectApiView(APIView):
    """
    Add/Update Project
    """
    authentication_classes = [OAuth2Authentication]

    @staticmethod
    def post(request):
        try:
            data = request.data
            if "site_id" in data and data['site_id'] != "":
                site_id = int(data['site_id'])
                network = NetworkDomain.objects.filter(id=site_id, is_active=1).first()
                if network is None:
                    return Response(response.parsejson("Site not exist.", "", status=403))
                data['domain'] = site_id
            else: return Response(response.parsejson("site_id is required", "", status=403))

            project_id = None
            check_update = None
            if "project_id" in data and data['project_id'] != "":
                project_id = int(data['project_id'])
                check_update = True
                project_id = DeveloperProject.objects.filter(id=project_id, domain=site_id).first()
                if project_id is None: return Response(response.parsejson("Project not exist.", "", status=403))

            if "step" in data and data['step'] != "": step = int(data['step'])
            else: return Response(response.parsejson("step is required.", "", status=403))

            user_domain = None
            creater_user_type = None
            if "user_id" in data and data['user_id'] != "":
                user_id = int(data['user_id'])
                users = Users.objects.filter(id=user_id, site=site_id, user_type=2, status=1).first()
                if users is None:
                    users = Users.objects.filter(id=user_id, user_type=2, status=1).first()
                    if users is None:
                        users = Users.objects.filter(id=user_id, network_user__domain=site_id, network_user__is_agent=1, network_user__status=1, status=1, user_type=4).first()
                        if users is None:
                            return Response(response.parsejson("User not exist.", "", status=403))
                if project_id is not None and project_id.agent_id is not None:
                    user_id = project_id.agent_id
                else:
                    data["added_by"] = user_id
                data["agent"] = user_id
                user_domain = users.site_id
                creater_user_type = users.user_type_id
            else:
                return Response(response.parsejson("user_id is required.", "", status=403))
            if step == 1:
                if "project_name" in data and data['project_name'] != "": project_name = data['project_name']
                else: return Response(response.parsejson("project_name is required.", "", status=403))

                if "country" in data and data['country'] != "": country = data['country']
                else: return Response(response.parsejson("country is required.", "", status=403))

                if "city" in data and data['city'] != "": city = data['city']
                else: return Response(response.parsejson("city is required.", "", status=403))

                if "neighborhood" in data and data['neighborhood'] != "": neighborhood = data['neighborhood']
                else: return Response(response.parsejson("neighborhood is required.", "", status=403))

                if "community" in data and data['community'] != "": community = data['community']
                else: return Response(response.parsejson("community is required.", "", status=403))

                if "address_one" in data and data['address_one'] != "": address_one = data['address_one']
                else: return Response(response.parsejson("address_one is required.", "", status=403))

                if "postal_code" in data and data['postal_code'] != "": postal_code = data['postal_code']
                else: return Response(response.parsejson("postal_code is required.", "", status=403))

                if "registration_number" in data and data['registration_number'] != "": registration_number = data['registration_number']
                else: return Response(response.parsejson("registration_number is required.", "", status=403))

                if "registration_date" in data and data['registration_date'] != "":
                    registration_date = datetime.strptime(data['registration_date'], "%m-%d-%Y %I:%M %p")
                    data['registration_date'] = registration_date.isoformat()
                else: return Response(response.parsejson("registration_date is required.", "", status=403))

                if "completion_date" in data and data['completion_date'] != "":
                    completion_date = datetime.strptime(data['completion_date'], "%m-%d-%Y %I:%M %p")
                    data['completion_date'] = completion_date.isoformat()
                else: return Response(response.parsejson("completion_date is required.", "", status=403))

                if "starting_price" in data and data['starting_price'] != "": property_type = data['starting_price']
                else: return Response(response.parsejson("starting_price is required.", "", status=403))

                if "total_units" in data and data['total_units'] != "": total_units = data['total_units']
                else: return Response(response.parsejson("total_units is required.", "", status=403))

                if "units_for_sale" in data and data['units_for_sale'] != "": units_for_sale = data['units_for_sale']
                else: return Response(response.parsejson("units_for_sale is required.", "", status=403))

                if "units_type" in data and data['units_type'] != "": units_type = data['units_type']
                else: return Response(response.parsejson("units_type is required.", "", status=403))

                if "property_size" in data and data['property_size'] != "": property_size = data['property_size']
                else: return Response(response.parsejson("property_size is required.", "", status=403))

                if "project_desc" in data and data['project_desc'] != "": project_desc = data['project_desc']
                else: return Response(response.parsejson("project_desc is required.", "", status=403))

                if "project_status" in data and data['project_status'] != "": project_status = int(data["project_status"])
                else: project_status = 2

                if "status" in data and data['status'] != "":
                    data['status'] = int(data['status'])
                else:
                    data['status'] = 2

                if "is_approved" in data and data['is_approved'] != "":
                    data['is_approved'] = bool(data['status'])
                else:
                    data['is_approved'] = 0

                data["create_step"] = 1
                data["title"] = "testing"

                serializer = AddDeveloperProjectSerializer(project_id, data=data)
                if serializer.is_valid():
                    project_id = serializer.save()
                    project_id = project_id.id
                else:
                    copy_errors = serializer.errors.copy()
                    return Response(response.parsejson(copy_errors, "", status=403))

                # ----------------------Property Type---------------------
                # if "project_type" in data and type(data["project_type"]) == list:
                #     project_type = data["project_type"]
                #     DeveloperProjectType.objects.filter(project=project_id).delete()
                #     for prop_type in project_type:
                #         project_type = DeveloperProjectType()
                #         project_type.project_id = project_id
                #         project_type.project_type_id = prop_type
                #         project_type.save()

                if "project_type" in data and isinstance(data["project_type"], list):
                    project_type_list = data["project_type"]
                    existing_project_type_ids = set(
                        DeveloperProjectType.objects.filter(project_id=project_id)
                        .values_list("project_type_id", flat=True)
                    )
                    project_type_list = list(map(int, project_type_list))
                    to_remove = list(existing_project_type_ids.symmetric_difference(set(project_type_list)))
                    to_add = [prop_type for prop_type in project_type_list if prop_type not in existing_project_type_ids]
                    DeveloperProjectType.objects.filter(project_id=project_id, project_type_id__in=to_remove).delete()
                    DeveloperProjectType.objects.bulk_create([
                        DeveloperProjectType(project_id=project_id, project_type_id=prop_type)
                        for prop_type in to_add
                    ])

                # ----------------------Selected Facility---------------------
                if "selected_facility" in data and type(data["selected_facility"]) == list:
                    selected_facility = data["selected_facility"]
                    DeveloperProjectSelectedFacility.objects.filter(project=project_id).delete()
                    for facility in selected_facility:
                        project_selected_facility = DeveloperProjectSelectedFacility()
                        project_selected_facility.project_id = project_id
                        project_selected_facility.facility_id = facility
                        project_selected_facility.save()

                try:
                    developer_project = DeveloperProject.objects.get(id=project_id)
                except:
                    pass
            elif step == 2:
                if project_id is None: return Response(response.parsejson("project_id is required.", "", status=403))
                project_id = project_id.id
                if "is_map_view" in data and data["is_map_view"] != "": is_map_view = data["is_map_view"]
                else: return Response(response.parsejson("is_map_view is required.", "", status=403))

                if "is_street_view" in data and data["is_street_view"] != "": is_street_view = data["is_street_view"]
                else: return Response(response.parsejson("is_street_view is required.", "", status=403))

                if "is_arial_view" in data and data["is_arial_view"] != "": is_arial_view = data["is_arial_view"]
                else: return Response(response.parsejson("is_arial_view is required.", "", status=403))

                map_url = None
                if "map_url" in data and data['map_url'] != "": map_url = data['map_url']
                # else:
                #     return Response(response.parsejson("map_url is required.", "", status=403))

                latitude = None
                if "latitude" in data and data['latitude'] != "": latitude = data['latitude']

                longitude = None
                if "longitude" in data and data['longitude'] != "": longitude = data['longitude']

                developer_project = DeveloperProject.objects.get(id=project_id)
                developer_project.is_map_view = is_map_view
                developer_project.is_street_view = is_street_view
                developer_project.is_arial_view = is_arial_view
                developer_project.create_step = 2
                developer_project.map_url = map_url
                developer_project.latitude = latitude
                developer_project.longitude = longitude
                developer_project.save()
                DeveloperProjectNearByPlaces.objects.filter(project=project_id).delete()
                for key in ["SHOPPING","SCHOOL","HOSPITAL","LIFESTYLE"]:
                    project_place_json = DeveloperProjectNearByPlaces()
                    project_place_json.places_json = data[key]
                    project_place_json.place_type = key
                    project_place_json.project_id = project_id
                    project_place_json.save()
            elif step == 3:
                if project_id is None:
                    return Response(response.parsejson("project_id is required.", "", status=403))
                project_id = project_id.id
                if "project_pic" in data and type(data["project_pic"]) == list and len(data["project_pic"]) > 0:
                    project_pic = data["project_pic"]
                    DeveloperProjectUploads.objects.filter(project=project_id, upload_type=1).delete()
                    cnt = 0
                    for pic in project_pic:
                        project_uploads = DeveloperProjectUploads()
                        project_uploads.upload_id = pic
                        project_uploads.project_id = project_id
                        project_uploads.upload_type = 1
                        project_uploads.status_id = 1
                        project_uploads.photo_description = data['photo_description'][cnt] if len(data['photo_description']) and data['photo_description'][cnt] is not None and data['photo_description'][cnt] !='' else ""
                        project_uploads.save()
                        cnt +=1

                if "project_video" in data and type(data["project_video"]) == list and len(data["project_video"]) > 0:
                    project_video = data["project_video"]
                    DeveloperProjectUploads.objects.filter(project=project_id, upload_type=2).delete()
                    for video in project_video:
                        project_uploads = DeveloperProjectUploads()
                        project_uploads.upload_id = video
                        project_uploads.project_id = project_id
                        project_uploads.upload_type = 2
                        project_uploads.status_id = 1
                        project_uploads.save()

                developer_project = DeveloperProject.objects.get(id=project_id)
                developer_project.create_step = 3
                developer_project.save()
            elif step == 4:
                if project_id is None:
                    return Response(response.parsejson("project_id is required.", "", status=403))
                project_id = project_id.id
                if "floor_plans" in data and type(data["floor_plans"]['floor_headings']) == list and len(data["floor_plans"]['floor_headings']) > 0:
                    floor_length = len(data["floor_plans"]['floor_headings'])
                    DeveloperProjectFloorPlans.objects.filter(project=project_id).delete()
                    for i in range(floor_length):
                        heading=data["floor_plans"]['floor_headings'][i],
                        bed_rooms=data["floor_plans"]['floor_bedrooms'][i],
                        available_units=data["floor_plans"]['floor_available_units'][i],
                        area=data["floor_plans"]['floor_area'][i],
                        bedroom_desc=data["floor_plans"]['floor_bedroom_desc'][i],
                        project_type_id = data["floor_plans"]['project_type_id'][i],
                        floor_plan_img_id=data["floor_plans"]['floor_plan_img_id'][i] if len(data["floor_plans"]['floor_plan_img_id']) > i else None

                        if heading[0] != '' and bed_rooms[0] != '' and available_units[0] != '' and area[0] != '' and bedroom_desc[0] != '' and project_type_id[0] != '':
                            floor_plan_uploads = DeveloperProjectFloorPlans()
                            floor_plan_uploads.project_id = project_id
                            floor_plan_uploads.upload_id = floor_plan_img_id
                            floor_plan_uploads.project_type_id = project_type_id[0]
                            floor_plan_uploads.floor_heading = heading[0]
                            floor_plan_uploads.floor_bed_rooms = bed_rooms[0]
                            floor_plan_uploads.floor_available_units = available_units[0]
                            floor_plan_uploads.floor_area = area[0]
                            floor_plan_uploads.floor_bedroom_desc = bedroom_desc[0]
                            floor_plan_uploads.status_id = 1
                            floor_plan_uploads.save()

                if "project_documents" in data and type(data["project_documents"]) == list and len(data["project_documents"]) > 0:
                    project_documents = data["project_documents"]
                    DeveloperProjectUploads.objects.filter(project=project_id, upload_type=3).delete()
                    for documents in project_documents:
                        project_uploads = DeveloperProjectUploads()
                        project_uploads.upload_id = documents
                        project_uploads.project_id = project_id
                        project_uploads.upload_type = 3
                        project_uploads.status_id = 1
                        project_uploads.save()

                developer_project = DeveloperProject.objects.get(id=project_id)
                developer_project.create_step = 4
                developer_project.save()

            all_data = {"project_id": project_id}

            return Response(response.parsejson("Property added/updated successfully.", all_data, status=201))
        except Exception as exp:
            print(exp)
            return Response(response.parsejson(str(exp), exp, status=403))

class DeveloperProjectDetailApiView(APIView):
    """
    Developer project detail
    """
    authentication_classes = [OAuth2Authentication]

    @staticmethod
    def post(request):
        try:
            data = request.data
            if "site_id" in data and data['site_id'] != "":
                site_id = int(data['site_id'])
                network = NetworkDomain.objects.filter(id=site_id, is_active=1).first()
                if network is None:
                    return Response(response.parsejson("Site not exist.", "", status=403))
            else:
                return Response(response.parsejson("site_id is required", "", status=403))

            if "project_id" in data and data['project_id'] != "":
                project_id = int(data['project_id'])
            else:
                return Response(response.parsejson("project_id is required", "", status=403))

            if "step_id" in data and data['step_id'] != "":
                step_id = int(data['step_id'])
            else:
                return Response(response.parsejson("step_id is required", "", status=403))
            developer_project_details = DeveloperProject.objects.get(id=project_id, domain=site_id)
            if step_id == 1:
                serializer = DeveloperProjectDetailStepOneSerializer(developer_project_details)
            elif step_id == 2:
                serializer = DeveloperProjectDetailStepTwoSerializer(developer_project_details)
            elif step_id == 3:
                serializer = DeveloperProjectDetailStepThreeSerializer(developer_project_details)
            elif step_id == 4:
                developer_project_details = DeveloperProject.objects.filter(id=project_id, domain=site_id).prefetch_related(
                    Prefetch(
                        'developer_project_type',
                        queryset=DeveloperProjectType.objects.prefetch_related(
                            Prefetch('developer_project_floor_plans')
                        )
                    )
                )
                serializer = DeveloperProjectDetailStepFourSerializer(developer_project_details, many=True)

            return Response(response.parsejson("Fetch Data.", serializer.data, status=201))
        except Exception as exp:
            print(exp)
            return Response(response.parsejson(str(exp), exp, status=403))

class AddDeveloperProjectVideoApiView(APIView):
    """
    Developer add project video
    """
    authentication_classes = [OAuth2Authentication]

    @staticmethod
    def post(request):
        try:
            data = request.data
            if "site_id" in data and data['site_id'] != "":
                site_id = int(data['site_id'])
                network = NetworkDomain.objects.filter(id=site_id, is_active=1).first()
                if network is None:
                    return Response(response.parsejson("Site not exist.", "", status=403))
            else:
                return Response(response.parsejson("site_id is required", "", status=403))

            if "user_id" in data and data['user_id'] != "":
                user_id = int(data['user_id'])
                users = Users.objects.filter(id=user_id, user_type=2, status=1).first() # site=site_id
                if users is None:
                    users = Users.objects.filter(id=user_id, network_user__domain=site_id, network_user__is_agent=1,
                                                 network_user__status=1, status=1, user_type=4).first()
                    if users is None:
                        return Response(response.parsejson("User not exist.", "", status=403))
            else:
                return Response(response.parsejson("user_id is required.", "", status=403))


            if "video_url" in data and data['video_url'] != "":
                video_url = data['video_url']
            else:
                return Response(response.parsejson("video_url is required.", "", status=403))

            user_uploads = UserUploads()
            user_uploads.user_id = user_id
            user_uploads.site_id = site_id
            user_uploads.doc_file_name = video_url
            user_uploads.added_by_id = user_id
            user_uploads.updated_by_id = user_id
            user_uploads.save()
            upload_id = user_uploads.id
            all_data = {"upload_id": upload_id, "video_url": video_url}
            return Response(response.parsejson("Video added successfully.", all_data, status=201))
        except Exception as exp:
            return Response(response.parsejson(str(exp), exp, status=403))

class DeveloperProjectDocumentDeleteApiView(APIView):
    """
    Develope project document delete
    """
    authentication_classes = [OAuth2Authentication]

    @staticmethod
    def post(request):
        try:
            data = request.data
            if "site_id" in data and data['site_id'] != "":
                site_id = int(data['site_id'])
                network = NetworkDomain.objects.filter(id=site_id, is_active=1).first()
                if network is None:
                    return Response(response.parsejson("Site not exist.", "", status=403))
            else:
                return Response(response.parsejson("site_id is required", "", status=403))

            if "user_id" in data and data['user_id'] != "":
                user_id = int(data['user_id'])
                users = Users.objects.filter(id=user_id, user_type=2, status=1).first()
                if users is None:
                    users = Users.objects.filter(id=user_id, network_user__domain=site_id, network_user__is_agent=1,
                                                 network_user__status=1, status=1, user_type=2).first()
                    if users is None:
                        return Response(response.parsejson("User not exist.", "", status=403))
            else:
                return Response(response.parsejson("user_id is required.", "", status=403))

            if "project_id" in data and data['project_id'] != "":
                project_id = int(data['project_id'])
                project_id = DeveloperProject.objects.filter(id=project_id, domain=site_id).first()
                if project_id is None:
                    return Response(response.parsejson("Project not exist.", "", status=403))
            else:
                return Response(response.parsejson("project_id is required.", "", status=403))

            if "upload_id" in data and data['upload_id'] != "":
                upload_id = int(data['upload_id'])
            else:
                return Response(response.parsejson("upload_id is required.", "", status=403))

            DeveloperProjectUploads.objects.filter(upload=upload_id, project=project_id, project__domain=site_id).delete()
            UserUploads.objects.filter(id=upload_id, site=site_id).delete()
            return Response(response.parsejson("Delete successfully.", "", status=201))
        except Exception as exp:
            print(exp)
            return Response(response.parsejson(str(exp), exp, status=403))

class DeveloperProjectFloorPlanDeleteApiView(APIView):
    """
    Delete floor plan file
    """
    authentication_classes = [OAuth2Authentication]

    @staticmethod
    def post(request):
        try:
            data = request.data
            if "user_id" in data and data['user_id'] != "":
                user_id = int(data['user_id'])
                user = Users.objects.filter(id=user_id).first()
                if user is None:
                    return Response(response.parsejson("User not exist.", "", status=403))
            else:
                user_id = None

            if "upload_id" in data and data['upload_id'] != "":
                upload_id = int(data['upload_id'])
            else:
                return Response(response.parsejson("upload_id is required", "", status=403))

            if "upload_type" in data and data['upload_type'] != "":
                upload_type = data['upload_type'].lower()
            else:
                return Response(response.parsejson("upload_type is required", "", status=403))

            with transaction.atomic():
                try:
                    if upload_type == "floor_plans" and user_id is not None:
                        DeveloperProjectFloorPlans.objects.filter(upload=upload_id).update(upload=None)
                    UserUploads.objects.filter(id=upload_id).delete()
                except Exception as exp:
                    transaction.set_rollback(True)
                    return Response(response.parsejson(str(exp), exp, status=403))
            return Response(response.parsejson("Success.", "", status=201))
        except Exception as exp:
            return Response(response.parsejson(str(exp), exp, status=403))

class AddFacilityListApiView(APIView):
    """
    Developer add new facility details
    """
    authentication_classes = [OAuth2Authentication]

    @staticmethod
    def post(request):
        try:
            data = request.data
            if "site_id" in data and data['site_id'] != "":
                site_id = int(data['site_id'])
                network = NetworkDomain.objects.filter(id=site_id, is_active=1).first()
                if network is None:
                    return Response(response.parsejson("Site not exist.", "", status=403))
            else:
                return Response(response.parsejson("site_id is required", "", status=403))

            if "user_id" in data and data['user_id'] != "":
                user_id = int(data['user_id'])
                users = Users.objects.filter(id=user_id, user_type=2, status=1).first() # site=site_id
                if users is None:
                    users = Users.objects.filter(id=user_id, network_user__domain=site_id, network_user__is_agent=1,
                                                 network_user__status=1, status=1, user_type=4).first()
                    if users is None:
                        return Response(response.parsejson("User not exist.", "", status=403))
            else:
                return Response(response.parsejson("user_id is required.", "", status=403))

            if "facility_name" in data and data['facility_name'] != "":
                facility_name = data['facility_name']
            else:
                return Response(response.parsejson("facility_name is required.", "", status=403))

            if "facility_img_id" in data and data['facility_img_id'] != "":
                facility_img_id = data['facility_img_id']
            else:
                return Response(response.parsejson("facility_img_id is required.", "", status=403))

            project_facility = DeveloperProjectFacility()
            project_facility.name = facility_name
            project_facility.upload_id = facility_img_id
            project_facility.save()
            facility_id = project_facility.id

            project_id = None
            if facility_id != "" and "project_id" in data and data['project_id'] != "":
                project_id = data['project_id']
                project_selected_facility = DeveloperProjectSelectedFacility()
                project_selected_facility.project_id = project_id
                project_selected_facility.facility_id = facility_id
                project_selected_facility.save()

            all_data = {"facility_id": facility_id, "project_id": project_id}
            return Response(response.parsejson("Facility added successfully.", all_data, status=201))
        except Exception as exp:
            return Response(response.parsejson(str(exp), exp, status=403))

class DeveloperProjectStatusChangeApiView(APIView):
    """
    Project status change
    """
    authentication_classes = [OAuth2Authentication]

    @staticmethod
    def post(request):
        try:
            data = request.data
            if "site_id" in data and data['site_id'] != "":
                site_id = int(data['site_id'])
                network = NetworkDomain.objects.filter(id=site_id, is_active=1).first()
                if network is None:
                    return Response(response.parsejson("Site not exist.", "", status=403))
            else:
                # Translators: This message appears when site_id is empty
                return Response(response.parsejson("site_id is required", "", status=403))

            if "user_id" in data and data['user_id'] != "":
                user_id = int(data['user_id'])
                users = Users.objects.filter(id=user_id, user_type=2, status=1).first()
                print(user_id)
                if users is None:
                    return Response(response.parsejson("You are not authentic user to update property.", "", status=403))
            else:
                # Translators: This message appears when user_id is empty
                return Response(response.parsejson("user_id is required.", "", status=403))

            if "project_id" in data and data['project_id'] != "":
                project_id = int(data['project_id'])
            else:
                # Translators: This message appears when project_id is empty
                return Response(response.parsejson("project_id is required", "", status=403))

            if "status" in data and data['status'] != "":
                status = data['status']
            else:
                # Translators: This message appears when status is empty
                return Response(response.parsejson("status is required", "", status=403))

            DeveloperProject.objects.filter(id=project_id, domain=site_id).update(status_id=status)
            return Response(response.parsejson("Status changed successfully..", "", status=201))
        except Exception as exp:
            return Response(response.parsejson(str(exp), exp, status=403))

class DeveloperProjectApprovalChangeApiView(APIView):
    """
    Project approval change
    """
    authentication_classes = [OAuth2Authentication]

    @staticmethod
    def post(request):
        try:
            data = request.data
            if "site_id" in data and data['site_id'] != "":
                site_id = int(data['site_id'])
                network = NetworkDomain.objects.filter(id=site_id, is_active=1).first()
                if network is None:
                    return Response(response.parsejson("Site not exist.", "", status=403))
            else:
                # Translators: This message appears when site_id is empty
                return Response(response.parsejson("site_id is required", "", status=403))

            if "user_id" in data and data['user_id'] != "":
                user_id = int(data['user_id'])
                users = Users.objects.filter(id=user_id, site=site_id, user_type=2, status=1).first()
                if users is None:
                    users = Users.objects.filter(id=user_id, user_type=2, status=1).first()
                    if users is None:
                        return Response(response.parsejson("You are not authentic user to update property.", "", status=403))
            else:
                # Translators: This message appears when user_id is empty
                return Response(response.parsejson("user_id is required.", "", status=403))

            if "project_id" in data and data['project_id'] != "":
                project_id = int(data['project_id'])
            else:
                # Translators: This message appears when project_id is empty
                return Response(response.parsejson("project_id is required", "", status=403))

            if "is_approved" in data and data['is_approved'] != "":
                is_approved = data['is_approved']
            else:
                # Translators: This message appears when is_approved is empty
                return Response(response.parsejson("is_approved is required", "", status=403))

            DeveloperProject.objects.filter(id=project_id, domain=site_id).update(is_approved=is_approved)

            return Response(response.parsejson("Approval changed successfully..", "", status=201))
        except Exception as exp:
            return Response(response.parsejson(str(exp), exp, status=403))

class SubdomainProjectListingApiView(APIView):
    """
    Subdomain Project listing
    """
    authentication_classes = [OAuth2Authentication, TokenAuthentication]

    @staticmethod
    def post(request):
        try:
            data = request.data
            offset = 0
            if 'page_size' in data and data['page_size'] != "":
                limit = int(data['page_size'])
            else:
                limit = int(settings.LIST_PER_PAGE)

            if 'page' in data and data['page'] != "":
                page = int(data['page'])
            else:
                page = 1
            # -----------Set Pagination Value--------
            if limit > 0:
                offset = (page - 1) * limit
                limit = limit * page

            if "site_id" in data and data['site_id'] != "":
                site_id = int(data['site_id'])
                network = NetworkDomain.objects.filter(id=site_id, is_active=1).first()
                if network is None:
                    return Response(response.parsejson("Site not exist.", "", status=403))
            else:
                return Response(response.parsejson("site_id is required", "", status=403))

            project_listing = DeveloperProject.objects.filter(domain=site_id, status = 1, is_approved=1).exclude(project_status=5)
            if "is_featured" in data and data['is_featured'] != "" and data['is_featured'] == 1:
                project_listing = project_listing.filter(is_featured=1)
            elif "is_featured" in data and data['is_featured'] != "" and data['is_featured'] == 2:
                project_listing = project_listing.exclude(is_featured=1)   

            # -----------------Filter-------------------

            if "status" in data and data["status"] != "":
                status = int(data["status"])
                project_listing = project_listing.filter(Q(project_status=status))

            if "project_type" in data and data["project_type"] != "":
                project_type = int(data["project_type"])
                project_listing = project_listing.filter(Q(developer_project_type__project_type=project_type))

            # -----------------Search-------------------
            if 'search' in data and data['search'] != "":
                search = data['search'].strip()
                # project_listing = project_listing.annotate(project_name=Concat('address_one', V(', '), 'city', V(', '), 'state__state_name', V(' '), 'postal_code', output_field=CharField())).annotate(full_name=Concat('agent__user_business_profile__first_name', V(' '), 'agent__user_business_profile__last_name')).filter(Q(property_asset__name__icontains=search) | Q(sale_by_type__auction_type__icontains=search) | Q(agent__user_business_profile__company_name__icontains=search) | Q(full_name__icontains=search) | Q(city__icontains=search) | Q(address_one__icontains=search) | Q(state__state_name__icontains=search) | Q(property_type__property_type__icontains=search) | Q(property_name__icontains=search) | Q(postal_code__icontains=search))
                project_listing = DeveloperProject.objects.filter(domain=site_id, status = 1, is_approved=1).exclude(project_status=5)
                project_listing = project_listing.annotate(
                    annotated_project_name=Concat(
                        'address_one',
                        V(', '),
                        'city__state_name',
                        V(', '),
                        'country__country_name',
                        output_field=CharField()
                    )
                ).filter(
                    Q(project_name__icontains=search) |
                    Q(annotated_project_name__icontains=search) |
                    Q(agent__user_business_profile__company_name__icontains=search) |
                    Q(city__state_name__icontains=search) |
                    Q(address_one__icontains=search) |
                    Q(country__country_name__icontains=search) |
                    Q(neighborhood__icontains=search) |
                    Q(community__icontains=search) |
                    Q(postal_code__icontains=search)
                )

            total = project_listing.count()
            project_listing = project_listing.order_by(F("ordering").asc(nulls_last=True)).only("id")[offset:limit]
            serializer = SubdomainProjectListingSerializer(project_listing, many=True)
            all_data = {"data": serializer.data, "total": total}
            return Response(response.parsejson("Projects List.", all_data, status=201))
        except Exception as exp:
            return Response(response.parsejson(str(exp), exp, status=403))

class SubdomainProjectDetailApiView(APIView):
    """
    Subdomain Developer project detail
    """
    authentication_classes = [OAuth2Authentication, TokenAuthentication]

    @staticmethod
    def post(request):
        try:
            data = request.data
            if "site_id" in data and data['site_id'] != "":
                site_id = int(data['site_id'])
                network = NetworkDomain.objects.filter(id=site_id, is_active=1).first()
                if network is None:
                    return Response(response.parsejson("Site not exist.", "", status=403))
            else:
                return Response(response.parsejson("site_id is required", "", status=403))

            if "project_id" in data and data['project_id'] != "":
                try:
                    project_id = int(data["project_id"])
                    project_detail = DeveloperProject.objects.filter(id=project_id, domain=site_id, status = 1, is_approved=1).first()
                    if not project_detail:
                        return Response(response.parsejson("Project doesn't exist.", "", status=403))
                except ValueError:
                    return Response(response.parsejson("Invalid project_id provided.", "", status=403))
            else:
                return Response(response.parsejson("project_id is required", "", status=403))

            serializer = SubdomainProjectDetailSerializer(DeveloperProject.objects.filter(id=project_id, domain=site_id, status = 1, is_approved=1).prefetch_related(
                Prefetch(
                    'developer_project_type',
                    queryset=DeveloperProjectType.objects.prefetch_related(
                        Prefetch('developer_project_floor_plans')
                    )
                )
            ), many=True)

            return Response(response.parsejson("Project Detail Data.", serializer.data, status=201))
        except Exception as exp:
            print(exp)
            return Response(response.parsejson(str(exp), exp, status=403))
        

class ProjectListApiView(APIView):
    """
    Project List
    """
    authentication_classes = [OAuth2Authentication]

    @staticmethod
    def post(request):
        try:
            data = request.data
            if "site_id" in data and data['site_id'] != "":
                site_id = int(data['site_id'])
                network = NetworkDomain.objects.filter(id=site_id, is_active=1).first()
                if network is None:
                    return Response(response.parsejson("Site not exist.", "", status=403))
            else:
                return Response(response.parsejson("site_id is required", "", status=403))
            
            user_id = None
            if "user_id" in data and data['user_id'] != "":
                user_id = int(data['user_id'])
                users = Users.objects.filter(id=user_id, status=1).last()
                if users is None:
                    return Response(response.parsejson("User not exist.", "", status=403))
                
                if users.user_type_id == 2 and users.site_id is not None:
                    user_id = None
                elif users.user_type_id != 2:
                    network_user = NetworkUser.objects.filter(user_id=user_id).last()
                    user_id = network_user.developer_id if network_user is not None else None
                
            if user_id is None:
                projects = DeveloperProject.objects.filter(domain=site_id, status = 1, is_approved=1).order_by("project_name").values('id', 'project_name')
            else:
                projects = DeveloperProject.objects.filter(domain=site_id, agent=user_id, status = 1, is_approved=1).order_by("project_name").values('id', 'project_name')    
            return Response(response.parsejson("Project Detail Data.", projects, status=201))
        except Exception as exp:
            return Response(response.parsejson(str(exp), exp, status=403))        