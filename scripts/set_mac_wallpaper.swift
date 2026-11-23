import AppKit
import Foundation

func fail(_ message: String) -> Never {
    FileHandle.standardError.write(Data((message + "\n").utf8))
    exit(1)
}

guard CommandLine.arguments.count == 2 else {
    fail("Usage: set-wallpaper <image-path>")
}

let imagePath = (CommandLine.arguments[1] as NSString).standardizingPath
guard FileManager.default.fileExists(atPath: imagePath) else {
    fail("Wallpaper image does not exist: \(imagePath)")
}

let screens = NSScreen.screens
guard !screens.isEmpty else {
    fail("No active screens available to update wallpaper.")
}

let imageURL = URL(fileURLWithPath: imagePath)
let workspace = NSWorkspace.shared

for screen in screens {
    do {
        try workspace.setDesktopImageURL(imageURL, for: screen, options: [:])
    } catch {
        fail("Failed to set wallpaper on screen \(screen.localizedName): \(error)")
    }
}
