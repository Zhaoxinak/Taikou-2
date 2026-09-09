extends SceneTree
func _initialize():
    process_frame.connect(func():
        var env := Environment.new()
        var props := env.get_property_list()
        for p in props:
            var n := String(p["name"])
            if n.begins_with("dof") or n.begins_with("ssao") or n.begins_with("glow") or n.begins_with("tonemap") or n.begins_with("adjustment") or n.begins_with("ambient") or n.begins_with("background"):
                print(n)
        quit(0)
    , CONNECT_ONE_SHOT)
