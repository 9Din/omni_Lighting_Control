```{csv-table}
**Extension**: {{ extension_version }},**Documentation Generated**: {sub-ref}`today`
```

(omni.ui.scene)=

# Overview

SceneUI helps build great-looking 3d manipulators and 3d helpers with as little
code as possible. It provides shapes and controls for declaring the UI in 3D
space.




## Declarative syntax

SceneUI uses declarative syntax, so it's possible to state what the manipulator
should do. For example, you can write that you want an item list consisting of
an image and lines. The code is simpler and easier to read than ever before.

```execute 200
## Double comment means hide from shippet
from omni.ui import scene as sc
from omni.ui import color as cl
##
scene_view = sc.SceneView(
    aspect_ratio_policy=sc.AspectRatioPolicy.PRESERVE_ASPECT_FIT,
    height=200
)

with scene_view.scene:
    sc.Line([-0.5,-0.5,0], [-0.5, 0.5, 0], color=cl.red)
    sc.Line([-0.5,-0.5,0], [0.5, -0.5, 0], color=cl.green)
    sc.Arc(0.5, color=cl.documentation_nvidia)
```

This declarative style applies to complex concepts like interaction with the
mouse pointer. A gesture can be easily added to almost any item with a few lines
of code. The system handles all of the steps needed to compute the intersection
with the mouse pointer and depth sorting if you click many items at runtime.
With this easy input, your manipulator comes ready very quickly.

