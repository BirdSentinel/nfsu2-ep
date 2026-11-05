// Decode car texture blobs with the same HUFF/JDLZ codec used by Binarius.
// Arguments: source TEXTURES.BIN, output directory, Binarius library directory.
using System.Reflection;
using System.Runtime.InteropServices;

if (args.Length != 3) throw new ArgumentException("Expected texture pack, output directory and Binarius directory");
var libraryDirectory = Path.GetFullPath(args[2]);
AppDomain.CurrentDomain.AssemblyResolve += (_, e) => Assembly.LoadFrom(
    Path.Combine(libraryDirectory, new AssemblyName(e.Name).Name + ".dll"));
NativeLibrary.Load(Path.Combine(libraryDirectory, "LZCompressLib.dll"));
var library = Assembly.LoadFrom(Path.Combine(libraryDirectory, "Nikki.dll"));
var decompress = library.GetType("Nikki.Utils.Interop").GetMethod("Decompress",
    BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static);
var data = File.ReadAllBytes(args[0]);
Directory.CreateDirectory(args[1]);
for (int position = 8; position < data.Length - 8;)
{
    int tag = BitConverter.ToInt32(data, position);
    int size = BitConverter.ToInt32(data, position + 4);
    if (tag == unchecked((int)0xb3310000))
    {
        for (int child = position + 8; child < position + 8 + size;)
        {
            int childTag = BitConverter.ToInt32(data, child);
            int childSize = BitConverter.ToInt32(data, child + 4);
            if (childTag == 0x33310003)
            {
                for (int entry = child + 8; entry < child + 8 + childSize; entry += 24)
                {
                    uint key = BitConverter.ToUInt32(data, entry);
                    int offset = BitConverter.ToInt32(data, entry + 4);
                    int compressedSize = BitConverter.ToInt32(data, entry + 8);
                    var raw = (byte[])decompress.Invoke(null,
                        new object[] { data.AsSpan(offset, compressedSize).ToArray() });
                    File.WriteAllBytes(Path.Combine(args[1], key.ToString("x8") + ".raw"), raw);
                }
                Console.WriteLine($"Decoded {childSize / 24} car textures");
                return;
            }
            child += 8 + childSize;
        }
    }
    position += 8 + size;
}
throw new InvalidDataException("Car texture directory not found");
