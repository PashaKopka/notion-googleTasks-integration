def parse_checkbox(prop_name: str, prop_data: dict[str, str]) -> dict[str, str]:
    return {
        'name': prop_name,
        'value': prop_data['checkbox']
    }


def parse_title(prop_name: str, prop_data: dict[str, str]) -> dict[str, str]:
    return {
        'name': prop_name,
        'value': prop_data['title'][0]['text']['content']
        # TODO maybe make sens to add annotations (font parameters)
    }


def parse_last_edited_time(prop_name: str, prop_data: dict[str, str]) -> dict[str, str]:
    return {
        'name': prop_name,
        'value': prop_data['last_edited_time']  # TODO check it
    }


def notion_request_decorator(func):
    def wrapper(*args, **kwargs):
        res = func(*args, **kwargs)
        if res.status_code != 200:
            raise Exception(f'Notion request failed: {res.status_code}')
        return res
    return wrapper
