function switch_css() {
  css = document.getElementById("css-link");
  dswitch = document.getElementById("dark-switch");

  if (css.href.endsWith("/assets/style/main.css")) {
    post("/settings/dark_mode/1");
    css.href="/assets/style/main_dark.css";
    dswitch.classList.remove("fa-toggle-off");
    dswitch.classList.add("fa-toggle-on");
  }
  else {
    post("/settings/dark_mode/0");
    css.href="/assets/style/main.css";
    dswitch.classList.remove("fa-toggle-on");
    dswitch.classList.add("fa-toggle-off");
  }
}