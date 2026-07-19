from __future__ import annotations

from pathlib import Path


def main() -> None:
    homepage = Path("index.html")
    content = homepage.read_text(encoding="utf-8")

    archive_item = '<div class="menus_item"><a class="site-page" href="/archives/"><i class="fa-fw fa fa-archive"></i><span> 归档</span></a></div>'
    aircraft_item = '<div class="menus_item"><a class="site-page" href="/aircraft/"><i class="fa-fw fa fa-plane"></i><span> 飞机资料库</span></a></div>'
    if aircraft_item not in content:
        if archive_item not in content:
            raise RuntimeError("Unable to locate the Hexo navigation menu")
        content = content.replace(archive_item, archive_item + aircraft_item)

    existing_category = '<li class="categoryBar-list-item"><a class="categoryBar-list-link" href="/categories/%E9%A3%9E%E6%9C%BA%E8%B5%84%E6%96%99%E6%95%B4%E7%90%86/">飞机资料整理</a><span class="categoryBar-list-count">2</span></li>'
    aircraft_category = '<li class="categoryBar-list-item"><a class="categoryBar-list-link" href="/aircraft/">飞机资料库</a><span class="categoryBar-list-count">4</span></li>'
    if aircraft_category not in content:
        if existing_category not in content:
            raise RuntimeError("Unable to locate the homepage category bar")
        content = content.replace(existing_category, existing_category + aircraft_category)

    homepage.write_text(content, encoding="utf-8")
    print("Linked /aircraft/ from the blog homepage navigation and category bar")


if __name__ == "__main__":
    main()
