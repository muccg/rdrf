function hide_empty_menu() {
    var menu_element_count = $(".dropdown-menu-button ul li").length;

    if (menu_element_count == 0) {
        $(".dropdown-menu-button").hide();
    }
}
