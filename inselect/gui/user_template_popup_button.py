from PySide.QtGui import QAction, QFileDialog, QMenu, QPushButton

from inselect.lib.user_template import UserTemplate
from inselect.lib.utils import debug_print

from .user_template_choice import user_template_choice
from .utils import report_to_user


class UserTemplatePopupButton(QPushButton):
    "User template popup button"

    FILE_FILTER = u'Inselect user templates (*{0})'.format(
        UserTemplate.EXTENSION
    )

    def __init__(self, parent=None):
        super(UserTemplatePopupButton, self).__init__(parent)

        # Configure the UI
        self._create_actions()
        self.popup = QMenu()
        self.inject_actions(self.popup)
        self.setMenu(self.popup)

        user_template_choice().template_changed.connect(self.changed)

        # User template might already have been loaded so load the initial
        if user_template_choice().current:
            self.changed()

    def __del__(self):
        # Doing this prevents segfault on exit. Unsatisfactory.
        del self.popup

    def _create_actions(self):
        self._choose_action = QAction(
            "Choose...", self, triggered=self.choose
        )
        self._refresh_action = QAction(
            "Reload", self, triggered=self.refresh
        )
        self._default_action = QAction(
            u"Default ({0})".format(user_template_choice().DEFAULT.name),
            self, triggered=self.default
        )

    def inject_actions(self, menu):
        "Adds user template actions to menu"
        menu.addAction(self._choose_action)
        menu.addAction(self._refresh_action)
        menu.addSeparator()
        menu.addAction(self._default_action)

    @report_to_user
    def default(self):
        "Sets the default template"
        user_template_choice().select_default()

    @report_to_user
    def choose(self):
        "Shows a 'choose template' file dialog"
        debug_print('UserTemplateWidget.choose')
        path, selectedFilter = QFileDialog.getOpenFileName(
            self, "Choose user template",
            unicode(user_template_choice().last_directory()),
            self.FILE_FILTER
        )

        if path:
            # Save the user's choice
            user_template_choice().load(path)

    @report_to_user
    def refresh(self):
        debug_print('UserTemplateWidget.refresh')
        user_template_choice().refresh()

    def changed(self):
        "Slot for UserTemplateChoice.template_changed"
        debug_print('UserTemplateWidget.changed')
        choice = user_template_choice()
        self.setText(choice.current.name)
        self._refresh_action.setEnabled(not choice.current_is_default)
