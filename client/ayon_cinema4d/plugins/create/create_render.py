from ayon_cinema4d.api import (
    lib,
    plugin
)
from ayon_core.lib import EnumDef, BoolDef, UISeparatorDef
from ayon_core.pipeline.template_data import get_template_data_with_names
from ayon_core.pipeline import Anatomy, get_current_host_name
from ayon_core.lib import StringTemplate

class CreateRender(plugin.Cinema4DCreator):
    """Render"""
    identifier = "io.ayon.creators.cinema4d.render"
    label = "Render"
    description = "Create Render"
    product_type = "render"
    icon = "eye"

    # TODO: Enable this once it is implemented
    enabled = True

    # default render target
    render_target = "farm"

    default_variants = ["Main"]
    instance_attributes = ["review"]

    def get_instance_attr_defs(self):
        defs = lib.collect_animation_defs(self.create_context)

        self.log.debug(f"[RenderCreate] get_instance_attr_defs: {defs}")

        render_target_items = {
            "local": "Local",
            "farm": "Farm",
            "farm_split": "Farm - Split export & render jobs"
        }

        defs.append(
            EnumDef("render_target",
                    items=render_target_items,
                    label="Render Target",
                    default="farm")
        )

        defs.append(
            BoolDef("review",
                    label="Mark for Review",
                    default=True)
        )

        return defs

    def get_pre_create_attr_defs(self):
        return [
            BoolDef("use_selection",
                    tooltip="Attach instance to selected camera/null.",
                    default=True,
                    label="Use Selection"),
            UISeparatorDef(),
            EnumDef("render_target",
                    items={
                        "local": "Local",
                        "farm": "Farm",
                        "farm_split": "Farm - Split export & render jobs"
                    },
                    label="Render Target",
                    default="farm"),
            BoolDef(
                "mark_for_review",
                label="Review",
                default=True,
            )
        ]
    



