from .mongo_models import PostView, UserIntermediate, UserTimeline, CityList


class ViewPostRepository:

    @staticmethod
    def create_post_view(payload):
        view = PostView(**payload)
        return view.save()

    @staticmethod
    def get_one_by_user_id(user_id):
        try:
            return PostView.objects.filter(user_id=user_id,
                                           is_deleted=False).first()
        except Exception as err:
            print(str(err))
            return None

    @staticmethod
    def update(post_view, post_list):
        try:
            # def update_enterprise(store_front, payload, user_name=None):
            update_obj = {}
            update_obj['posts'] = post_list
            print(update_obj)
            return post_view.update(**update_obj)
        except Exception as err:
            print(str(err))
            return False


class UserTimeLineRepository:
    @staticmethod
    def get_one_by_user_id(user_id):
        try:
            return UserTimeline.objects.filter(user_id=user_id).first()
        except Exception as err:
            print(str(err))
            return None

    @staticmethod
    def create(payload):
        try:
            timeline = UserTimeline(**payload)
            return timeline.save()
        except Exception as err:
            print(str(err))
            return False

    @staticmethod
    def update(timeline, post_list,index):
        try:
            update_obj = {'is_deleted': False}
            update_obj['post_sequence'] = post_list
            update_obj['index'] = index
            print(update_obj)
            return timeline.update(**update_obj)
        except Exception as err:
            print(str(err))
            return False

    @staticmethod
    def get_all_timelines():
        try:
            return UserTimeline.objects.all()
        except Exception as err:
            return []

    @staticmethod
    def get_user_post(user_id, page, limit):
        print("555555555555",user_id)
        try:
            query = UserTimeline.objects.aggregate([
                {
                    '$match': {
                        "user_id": user_id
                    }
                },
                {
                    '$unwind': {
                        'path': "$post_sequence",
                        'preserveNullAndEmptyArrays': True
                    }
                },
                {
                    '$facet': {
                        "metadata": [{"$count": "total_data"},
                                     {"$addFields": {"current_page": page}},
                                     {"$addFields": {"limit": limit}}],
                        "data": [{"$skip": (page - 1) * limit}, {"$limit": limit}]
                    }
                }
            ])
            return list(query)
        except Exception as err:
            print(str(err))
            return []


class UserIntermediateRepository:
    @staticmethod
    def get_one_by_user_id(user_id):
        try:
            return UserIntermediate.objects.filter(user_id=user_id).first()
        except Exception as err:
            print(str(err))
            return None

    @staticmethod
    def create(payload):
        try:
            timeline = UserIntermediate(**payload)
            return timeline.save()
        except Exception as err:
            print(str(err))
            return False

    @staticmethod
    def update(intermediate, payload):
        try:
            update_obj = {'is_deleted': False}
            if 'post_sequence' in payload:
                update_obj['post_sequence'] = payload['post_sequence']
            if 'is_dumped' in payload:
                update_obj['is_dumped'] = payload['is_dumped']
            print(update_obj)
            return intermediate.update(**update_obj)
        except Exception as err:
            print(str(err))
            return False


# city suggestion
class CityListRepository:
    @staticmethod
    def create_city_list(payload):
        view = CityList(**payload)
        return view.save()

    @staticmethod
    def update(city_list, iso2, iso3, country, cities):
        try:
            # def update_enterprise(store_front, payload, user_name=None):
            update_obj = {}
            update_obj['iso2'] = iso2
            update_obj['iso2'] = iso3
            update_obj['country'] = country
            update_obj['cities'] = cities
            print(update_obj)
            return city_list.update(**update_obj)
        except Exception as err:
            print(str(err))
            return False

    @staticmethod
    def get_city_list(keyword):
        search_city = CityList.objects(cities__icontains=keyword)
        result=[]
        for data in search_city:
            city_list={}
            city_list['city']=data.cities
            city_list['country']=data.country
            result.append(city_list)
        return result
