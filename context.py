# -*- coding: utf-8 -*-
import sys

from resources.lib import context

if len(sys.argv) > 1 and sys.argv[1] == "guideclick":
    context.guide_click()
else:
    context.run()
