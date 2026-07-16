global using Microsoft.VisualStudio.TestTools.UnitTesting;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text.RegularExpressions;
using System.Xml.Linq;

namespace PUS_C_Scala_Test
{
    [Flags]
    public enum ServiceVariation
    {
        UPER =              0b0000_0001,
        ACN =               0b0000_0010,
        CREATE_TESTS =      0b0000_0100,
        CREATE_SCALA =      0b0000_1000,
        CREATE_C =          0b0001_0000,
        COMPARE_ENCODINGS = 0b0010_0000,
        CREATE_PYTHON =     0b0100_0000,
        XER =               0b1000_0000,
    }

    class TestBasics
    {
        private readonly ServiceVariation ScalaAndC = ServiceVariation.CREATE_SCALA | ServiceVariation.CREATE_C;

        private readonly string scalaLang = "-Scala";
        private readonly string cLang = "-c";
        private readonly string pythonLang = "-python";
        private readonly string uperEnc = "--uper-enc";
        private readonly string acnEnc = "-ACN";
        private readonly string xerEnc = "-XER";
        private readonly string genTests = "-atc";
        private readonly List<string> stdArgs = ["-fp", "AUTO", "-typePrefix", "T", "-o"];

        private readonly string outFolderPrefix = "../../../../PUSCScalaTest/GenTests/";
        private readonly string outFolderTestFix = "Test/";
        private readonly string outFolderSuffixUPER = "UPER/PUSC_";
        private readonly string outFolderSuffixACN = "ACN/PUSC_";
        private readonly string outFolderSuffixXER = "XER/PUSC_";
        private readonly string outFolderSuffixScala = "/Scala";
        private readonly string outFolderSuffixC = "/C";
        private readonly string outFolderSuffixPython = "/Python";
        private readonly string inputFilePrefix = "../../../../PUSCScalaTest/asn1-pusc-lib-asn1CompilerTestInput/";

        private readonly string asn1FileEnding = ".asn1";
        private readonly string acnFileEnding = ".acn";

        private readonly string cConfig = "release";
        private readonly string cProject = "VsProject";

        private string[] CombineArgs(string outputFolder, string[] files, ServiceVariation sv)
        {
            var parList = new List<string>();
            if ((sv & ServiceVariation.CREATE_SCALA) == ServiceVariation.CREATE_SCALA)
                parList.Add(scalaLang);

            if ((sv & ServiceVariation.CREATE_C) == ServiceVariation.CREATE_C)
                parList.Add(cLang);
            
            if ((sv & ServiceVariation.CREATE_PYTHON) == ServiceVariation.CREATE_PYTHON)
                parList.Add(pythonLang);

            if ((sv & ServiceVariation.UPER) == ServiceVariation.UPER)
                parList.Add(uperEnc);

            if ((sv & ServiceVariation.ACN) == ServiceVariation.ACN)
                parList.Add(acnEnc);

            if ((sv & ServiceVariation.XER) == ServiceVariation.XER)
                parList.Add(xerEnc);

            if ((sv & ServiceVariation.CREATE_TESTS) == ServiceVariation.CREATE_TESTS)
                parList.Add(genTests);

            parList.AddRange(stdArgs);
            parList.Add(outputFolder);

            // add asn1 input
            var asn1Files = files.Select(s => inputFilePrefix + s + asn1FileEnding);
            parList.AddRange(asn1Files.Where(s => File.Exists(s)));
            var missingASNFiles = asn1Files.Where(s => !File.Exists(s));
            if (missingASNFiles.Any())
                Console.WriteLine("WARNING: ASN1 Files not found: " + String.Join(",", missingASNFiles));

            // add acn file input
            if ((sv & ServiceVariation.ACN) == ServiceVariation.ACN) {
                var acnFiles = files.Select(s => inputFilePrefix + s + acnFileEnding);
                parList.AddRange(acnFiles.Where(s => File.Exists(s)));

                var missingACNFiles = acnFiles.Where(s => !File.Exists(s));
                if (missingACNFiles.Any())
                    Console.WriteLine("WARNING: ACN Files not found: " + String.Join(",", missingACNFiles));
            }

            return parList.ToArray();
        }

        private string GetOutputFolder(string serviceName, ServiceVariation sv)
        {
            var ret = outFolderPrefix;

            if ((sv & ServiceVariation.CREATE_TESTS) == ServiceVariation.CREATE_TESTS)
                ret += outFolderTestFix;

            if ((sv & ServiceVariation.UPER) == ServiceVariation.UPER &&
                (sv & ServiceVariation.ACN) == ServiceVariation.ACN)
            {
                ret += "ACN_" + outFolderSuffixUPER;
            }
            else
            {
                if ((sv & ServiceVariation.UPER) == ServiceVariation.UPER)
                    ret += outFolderSuffixUPER;

                if ((sv & ServiceVariation.ACN) == ServiceVariation.ACN)
                    ret += outFolderSuffixACN;

                if ((sv & ServiceVariation.XER) == ServiceVariation.XER)
                    ret += outFolderSuffixXER;
            }

            ret += serviceName;

            if ((sv & ServiceVariation.CREATE_SCALA) == ServiceVariation.CREATE_SCALA)
                ret += outFolderSuffixScala;
            else if ((sv & ServiceVariation.CREATE_C) == ServiceVariation.CREATE_C)
                ret += outFolderSuffixC;
            else if ((sv & ServiceVariation.CREATE_PYTHON) == ServiceVariation.CREATE_PYTHON)
                ret += outFolderSuffixPython;
            else
                Assert.IsTrue(false, "can not do both");

            return ret;
        }

        public void Run_TestService(PUS_C_Service service, string folderSuffix, ServiceVariation sv)
        {
            // if (sv == 0 || (sv & ServiceVariation.UPER) != 0 && (sv & ServiceVariation.ACN) != 0)
            //     throw new InvalidOperationException("can't do nothing or both UPER and ACN");

            List<string> folders = [];
            
            if ((sv & ServiceVariation.CREATE_SCALA) == ServiceVariation.CREATE_SCALA)
            {
                // create Scala Files
                var scalaOutputDir = getCleanWorkingFolderPath(folderSuffix, sv & ~ServiceVariation.CREATE_C & ~ServiceVariation.CREATE_PYTHON);
                Run_Test(service, scalaOutputDir, sv & ~ServiceVariation.CREATE_C & ~ServiceVariation.CREATE_PYTHON);
                folders.Add(scalaOutputDir);
            }

            if ((sv & ServiceVariation.CREATE_C) == ServiceVariation.CREATE_C)
            {
                // create C Files
                var cOutputDir = getCleanWorkingFolderPath(folderSuffix, sv & ~ServiceVariation.CREATE_SCALA & ~ServiceVariation.CREATE_PYTHON);
                Run_Test(service, cOutputDir, sv & ~ServiceVariation.CREATE_SCALA & ~ServiceVariation.CREATE_PYTHON);
                folders.Add(cOutputDir);
            }

            if ((sv & ServiceVariation.CREATE_PYTHON) == ServiceVariation.CREATE_PYTHON)
            {
                // create Python Files
                var pythonOutputDir = getCleanWorkingFolderPath(folderSuffix, sv & ~ServiceVariation.CREATE_SCALA & ~ServiceVariation.CREATE_C);
                Run_Test(service, pythonOutputDir, sv & ~ServiceVariation.CREATE_SCALA & ~ServiceVariation.CREATE_C);
                pythonOutputDir = Path.Combine(pythonOutputDir, "output");
                folders.Add(pythonOutputDir);
            }

            if ((sv & ServiceVariation.COMPARE_ENCODINGS) == ServiceVariation.COMPARE_ENCODINGS)
            {
                Assert.IsTrue(folders.Count > 1);
                var isXer = (sv & ServiceVariation.XER) == ServiceVariation.XER;
                for (var i = 0; i < folders.Count; i++)
                {
                    for (var j = i + 1; j < folders.Count; j++)
                    {
                        if (isXer)
                            CompareXerTestCases(service, sv, folders[i], folders[j]);
                        else
                            CompareTestCases(service, sv, folders[i], folders[j]);
                    }
                }
            }
        }

        private void CompareTestCases(PUS_C_Service service, ServiceVariation sv, string folderA, string folderB)
        {
            var binsA = Directory.GetFiles(folderA, "*.dat").Order().ToArray();
            var binsB = Directory.GetFiles(folderB, "*.dat").Order().ToArray();

            Assert.IsTrue(binsA.Select(Path.GetFileName).SequenceEqual(binsB.Select(Path.GetFileName)), "Output did not create the same number of files");

            List<int> failedTests = [];
            for (var i = 0; i < binsA.Length; ++i)
            {
                using var f1 = File.OpenRead(binsA[i]);
                using var f2 = File.OpenRead(binsB[i]);
                using var r1 = new BinaryReader(f1);
                using var r2 = new BinaryReader(f2);

                // Assert.IsTrue(r1.BaseStream.Length == r2.BaseStream.Length, $"file length for {binsA[i]} and {binsB[i]} are different");
                if (r1.BaseStream.Length != r2.BaseStream.Length)
                {
                    Console.WriteLine($"file length for {binsA[i]} and {binsB[i]} are different");
                    failedTests.Add(i + 1);
                    continue;
                }

                var isSame = true;
                while (r1.BaseStream.Position < r1.BaseStream.Length && isSame)
                {
                    isSame &= r1.ReadByte() == r2.ReadByte();
                }

                if (!isSame)
                {
                    Console.WriteLine($"file {binsA[i]} contents are not equal to {binsB[i]}");
                    failedTests.Add(i + 1);
                }
                // Assert.IsTrue(isSame, $"file {binsA[i]} contents are not equal to {binsB[i]}");
            }
            
            Assert.IsTrue(failedTests.Count == 0, $"Some .dat files not identical! Deviations in: [{string.Join(", ", failedTests)}] - Correct: {binsA.Length - failedTests.Count}/{binsA.Length}");
        }

        /// <summary>
        /// Compare XER test case outputs between C (writes .xml) and Python (writes .dat).
        /// Uses normalized-XML + numeric-aware leaf comparison.
        /// Python may produce a strict subset of files (min-size filter); asserts Python ⊆ C
        /// and every shared file is semantically XML-equal.
        /// </summary>
        private void CompareXerTestCases(PUS_C_Service service, ServiceVariation sv, string cFolder, string pythonFolder)
        {
            // C produces .xml files in cFolder; Python produces .dat files in pythonFolder (already /output)
            var cFiles = Directory.GetFiles(cFolder, "*.xml")
                .ToDictionary(p => Path.GetFileNameWithoutExtension(p)!, p => p);
            var pyFiles = Directory.GetFiles(pythonFolder, "*.dat")
                .ToDictionary(p => Path.GetFileNameWithoutExtension(p)!, p => p);

            // Assert Python's set ⊆ C's set
            var pyOnlyNames = pyFiles.Keys.Except(cFiles.Keys).ToList();
            Assert.IsTrue(pyOnlyNames.Count == 0,
                $"Python produced XER files not present in C: [{string.Join(", ", pyOnlyNames)}]");

            // Compare intersection
            var sharedNames = cFiles.Keys.Intersect(pyFiles.Keys).OrderBy(x => x).ToList();
            Console.WriteLine($"XER interop: C={cFiles.Count} files, Python={pyFiles.Count} files, shared={sharedNames.Count}");
            Assert.IsTrue(sharedNames.Count > 0, "No shared XER test case files found to compare");

            List<string> failedTests = [];
            foreach (var name in sharedNames)
            {
                var cContent = File.ReadAllText(cFiles[name]).Trim();
                var pyContent = File.ReadAllText(pyFiles[name]).Trim();

                try
                {
                    var cDoc = XDocument.Parse(cContent);
                    var pyDoc = XDocument.Parse(pyContent);
                    if (!XmlSemanticEquals(cDoc.Root!, pyDoc.Root!))
                    {
                        Console.WriteLine($"XER mismatch for {name}:");
                        Console.WriteLine($"  C:  {cContent}");
                        Console.WriteLine($"  Py: {pyContent}");
                        failedTests.Add(name);
                    }
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"XML parse error for {name}: {ex.Message}");
                    Console.WriteLine($"  C:  {cContent}");
                    Console.WriteLine($"  Py: {pyContent}");
                    failedTests.Add(name);
                }
            }

            Assert.IsTrue(failedTests.Count == 0,
                $"XER XML semantic mismatches in {failedTests.Count}/{sharedNames.Count}: [{string.Join(", ", failedTests)}]");
        }

        /// <summary>
        /// Recursively compare two XElements for semantic XER equality:
        /// - Same local element name (ignore namespace)
        /// - Same child elements in order (recursively)
        /// - Leaf text: numeric compare if both parse as double (relative tol ~1e-9), else trimmed-string
        /// - Attributes compared by local name and trimmed value
        /// </summary>
        private static bool XmlSemanticEquals(XElement a, XElement b)
        {
            if (a.Name.LocalName != b.Name.LocalName)
                return false;

            // Compare attributes (by local name, sorted)
            var aAttrs = a.Attributes().OrderBy(x => x.Name.LocalName).ToList();
            var bAttrs = b.Attributes().OrderBy(x => x.Name.LocalName).ToList();
            if (aAttrs.Count != bAttrs.Count) return false;
            for (int i = 0; i < aAttrs.Count; i++)
            {
                if (aAttrs[i].Name.LocalName != bAttrs[i].Name.LocalName) return false;
                if (!LeafTextEqual(aAttrs[i].Value, bAttrs[i].Value)) return false;
            }

            // Get child elements (not text nodes)
            var aChildren = a.Elements().ToList();
            var bChildren = b.Elements().ToList();

            if (aChildren.Count != bChildren.Count)
                return false;

            if (aChildren.Count == 0)
            {
                // Leaf: compare text content
                return LeafTextEqual(a.Value, b.Value);
            }

            // Recurse on children
            for (int i = 0; i < aChildren.Count; i++)
            {
                if (!XmlSemanticEquals(aChildren[i], bChildren[i]))
                    return false;
            }
            return true;
        }

        /// <summary>
        /// Compare two leaf text values: numeric if both parse as double (rel tol 1e-9),
        /// else trimmed string equality.
        /// </summary>
        private static bool LeafTextEqual(string a, string b)
        {
            var at = a.Trim();
            var bt = b.Trim();
            if (double.TryParse(at, System.Globalization.NumberStyles.Any,
                    System.Globalization.CultureInfo.InvariantCulture, out var da) &&
                double.TryParse(bt, System.Globalization.NumberStyles.Any,
                    System.Globalization.CultureInfo.InvariantCulture, out var db))
            {
                // Numeric compare with relative tolerance
                if (da == 0.0 && db == 0.0) return true;
                var denom = Math.Max(Math.Abs(da), Math.Abs(db));
                return Math.Abs(da - db) / denom < 1e-9;
            }
            return at == bt;
        }

        private struct TestRange
        {
            public TestRange(int s, int e)
            {
                start = s;
                end = e;
                testRange = Enumerable.Range(s, e);
            }

            public TestRange(int s, int e, IEnumerable<int> ex)
            {
                start = s;
                end = e;
                testRange = Enumerable.Range(s, e).Except(ex);
            }

            public readonly int start;
            public readonly int end;
            public readonly IEnumerable<int> testRange;
        }

        /**
         *  Get Range of interop tests between Scala and C.
         *
         *  Exclude tests that do not work because the JVM does not
         *  support unsigned values.
         *
         */
        private TestRange getInteropTests(PUS_C_Service service, ServiceVariation sv)
        {
            if ((sv & ServiceVariation.UPER) != 0)
                return service switch
                {
                    PUS_C_Service.S1 => new TestRange(1, 67),
                    PUS_C_Service.S2 => new TestRange(1, 201, new[] { 80 }),
                    PUS_C_Service.S3 => new TestRange(1, 325, new[] { 80 }),
                    PUS_C_Service.S4 => new TestRange(1, 146, new[] { 80 }),
                    PUS_C_Service.S5 => new TestRange(1, 168, new[] { 80 }),
                    PUS_C_Service.S6 => new TestRange(1, 236, new[] { 80 }),
                    PUS_C_Service.S8 => new TestRange(1, 133, new[] { 80 }),
                    PUS_C_Service.S9 => new TestRange(1, 124, new[] { 80 }),
                    PUS_C_Service.S11 => new TestRange(1, 226, new[] { 80 }),
                    PUS_C_Service.S12 => new TestRange(1, 307, new[] { 80 }),
                    PUS_C_Service.S13 => new TestRange(1, 307, new[] { 80 }),
                    PUS_C_Service.S14 => new TestRange(1, 212, new[] { 80 }),
                    PUS_C_Service.S15 => new TestRange(1, 308, new[] { 80 }),
                    PUS_C_Service.S17 => new TestRange(1, 8, new[] { 80 }),
                    PUS_C_Service.S18 => new TestRange(1, 180, new[] { 80 }),
                    PUS_C_Service.S19 => new TestRange(1, 147, new[] { 80 }),
                    PUS_C_Service.ADDITIONAL_TEST_CASES => new TestRange(1, 200, new[] { 80 }),
                    _ => throw new InvalidOperationException("unknown service")
                };
            else if ((sv & ServiceVariation.ACN) != 0)
                return service switch
                {
                    PUS_C_Service.S1 => new TestRange(1, 59),
                    PUS_C_Service.S2 => new TestRange(1, 179, new[] { 80 }),
                    PUS_C_Service.S3 => new TestRange(1, 308, new[] { 80 }),
                    PUS_C_Service.S4 => new TestRange(1, 134, new[] { 80 }),
                    PUS_C_Service.S5 => new TestRange(1, 159, new[] { 80 }),
                    PUS_C_Service.S6 => new TestRange(1, 226, new[] { 80 }),
                    PUS_C_Service.S8 => new TestRange(1, 120, new[] { 80 }),
                    PUS_C_Service.S9 => new TestRange(1, 118, new[] { 80 }),
                    PUS_C_Service.S11 => new TestRange(1, 213, new[] { 80 }),
                    //PUS_C_Service.S12 => Enumerable.Range(1, 129).Except(new[] { 80 }),
                    PUS_C_Service.S13 => new TestRange(1, 129, new [] { 80 }),
                    PUS_C_Service.S14 => new TestRange(1, 202, new[] { 80 }),
                    PUS_C_Service.S15 => new TestRange(1, 291, new[] { 80 }),
                    PUS_C_Service.S17 => new TestRange(1, 8, new[] { 80 }),
                    PUS_C_Service.S18 => new TestRange(1, 172, new[] { 80 }),
                    PUS_C_Service.S19 => new TestRange(1, 141, new[] { 80 }),
                    PUS_C_Service.ADDITIONAL_TEST_CASES => new TestRange(1, 200, new[] { 80 }),
                    _ => throw new InvalidOperationException("unknown service")
                };
            else
                throw new InvalidOperationException("no coding for testing");
        }

        private string getCleanWorkingFolderPath(string folderSuffix, ServiceVariation sv)
        {
            var outDir = GetOutputFolder(folderSuffix, sv);
            //if (Directory.Exists(outDir))
            //    Directory.Delete(outDir, true);

            return outDir;
        }

        private void Run_Test(PUS_C_Service service, string folderPath, ServiceVariation sv)
        {
            var args = CombineArgs(folderPath, GetServiceFiles(service)(), sv);

            var createAndRunTests = (sv & ServiceVariation.CREATE_TESTS) == ServiceVariation.CREATE_TESTS;

            Console.WriteLine("Called Compiler with args:");
            foreach (var a in args)
                Console.WriteLine(a);
            Console.WriteLine("============= END OF ARGS =============");

            CompileASN(args);

            if ((sv & ServiceVariation.CREATE_SCALA) == ServiceVariation.CREATE_SCALA)
                CompileScala(folderPath, !createAndRunTests);
            else if ((sv & ServiceVariation.CREATE_C) == ServiceVariation.CREATE_C)
                CompileC(folderPath, !createAndRunTests);
            else if ((sv & ServiceVariation.CREATE_PYTHON) == ServiceVariation.CREATE_PYTHON)
                Console.WriteLine("Python does not need compilation.");
            else
                Assert.IsTrue(false, "no input created that could be tested");

            if (createAndRunTests)
            {
                if ((sv & ServiceVariation.CREATE_SCALA) == ServiceVariation.CREATE_SCALA)
                    RunScalaTests(folderPath, createAndRunTests);
                else if ((sv & ServiceVariation.CREATE_C) == ServiceVariation.CREATE_C)
                    RunCTests(folderPath, createAndRunTests);
                else if ((sv & ServiceVariation.CREATE_PYTHON) == ServiceVariation.CREATE_PYTHON)
                    RunPythonTests(folderPath, createAndRunTests);
            }
        }

        Func<string[]> GetServiceFiles(PUS_C_Service service) => () => ServiceFiles.Files(service);

        private void CompileASN(string[] args)
        {
            Assert.AreEqual(Program.main(args), 0);
        }

        private void CompileScala(string outDir, bool printOutput)
        {
            StartSBTWithArg(outDir, "sbt compile", "[success]", printOutput);
        }

        private void CompileC(string outDir, bool printOutput)
        {
            if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
                RunMSBuild(outDir);
            else
                RunMake(outDir);
        }

        private void RunScalaTests(string outDir, bool printOutput)
        {
            StartSBTWithArg(outDir, "sbt run", "[test success]", printOutput);
        }

        private void RunCTests(string outDir, bool printOutput)
        {
            using var proc = new Process();
            proc.StartInfo = new ProcessStartInfo
            {
                FileName = RuntimeInformation.IsOSPlatform(OSPlatform.Windows) ? "cmd.exe" : "bash",
                Arguments = RuntimeInformation.IsOSPlatform(OSPlatform.Windows) ? $"/C {cConfig}\\{cProject}.exe" : $"-c ./mainprogram",

                WorkingDirectory = outDir,
                UseShellExecute = false,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                RedirectStandardInput = false,
                CreateNoWindow = false,
            };
            proc.Start();
            var stdout = proc.StandardOutput.ReadToEnd();
            var worked = stdout.Contains("All test cases (") && stdout.Contains(") run successfully.");
            if (!worked)
            {
                Console.WriteLine("C test cases failed. Stdout:");
                Console.WriteLine(stdout);
                Console.WriteLine("Stderr:");
                Console.WriteLine(proc.StandardError.ReadToEnd());
            }

            Assert.IsTrue(worked, "C test cases failed");
        }

        private void RunPythonTests(string outDir, bool printOutput)
        {
            using var proc = new Process();
            proc.StartInfo = new ProcessStartInfo
            {
                FileName = RuntimeInformation.IsOSPlatform(OSPlatform.Windows) ? "cmd.exe" : "bash",
                Arguments = RuntimeInformation.IsOSPlatform(OSPlatform.Windows) ? "/C uvx --python 3.11 pytest" : "--login -c \"uvx --python 3.11 pytest\"",

                WorkingDirectory = outDir,
                UseShellExecute = false,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                RedirectStandardInput = false,
                CreateNoWindow = false,
            };
            proc.Start();
            var stdout = proc.StandardOutput.ReadToEnd();
            var stderr = proc.StandardError.ReadToEnd();
            proc.WaitForExit();

            // Parse pytest output for test results
            var failedMatch = Regex.Match(stdout, @"(\d+)\s+failed");
            var passedMatch = Regex.Match(stdout, @"(\d+)\s+passed");

            var failedCount = failedMatch.Success ? failedMatch.Groups[1].Value : "0";
            var passedCount = passedMatch.Success ? passedMatch.Groups[1].Value : "0";

            if (printOutput)
            {
                Console.WriteLine(stdout);
                if (!string.IsNullOrEmpty(stderr))
                    Console.WriteLine("STDERR: " + stderr);
            }

            var worked = proc.ExitCode == 0;
            if (!worked)
            {
                Console.WriteLine(stdout);
                if (!string.IsNullOrEmpty(stderr))
                    Console.WriteLine("STDERR: " + stderr);
            }

            if (failedMatch.Success || passedMatch.Success)
            {
                Console.WriteLine($"Python Tests: {passedCount} passed, {failedCount} failed");
            }
            
            Assert.IsTrue(worked, "python test cases failed");
        }

        private void RunMake(string outDir)
        {
            using (var proc = new Process
            {
                StartInfo = new ProcessStartInfo
                {
                    FileName = "bash",
                    Arguments = "-c make all",
                    WorkingDirectory = outDir,
                    UseShellExecute = false,
                    RedirectStandardOutput = true,
                    RedirectStandardInput = true,
                    CreateNoWindow = false,
                }
            })
            {
                proc.Start();

                // parse output
                var stdout = proc.StandardOutput.ReadToEnd();
                Console.WriteLine(stdout);
            }
        }

        private void RunMSBuild(string outDir)
        {
            // get latest installed MS Build
            var msBuildPath = "";
            using (var proc = new Process
            {
                StartInfo = new ProcessStartInfo
                {
                    FileName = @$"{Environment.GetEnvironmentVariable("ProgramFiles(x86)")}\Microsoft Visual Studio\Installer\vswhere.exe",
                    Arguments = @"-latest -requires Microsoft.Component.MSBuild -find MSBuild\**\Bin\msbuild.exe",
                    UseShellExecute = false,
                    RedirectStandardOutput = true,
                    RedirectStandardInput = false,
                    CreateNoWindow = true,
                }
            })
            {
                proc.Start();
                var stdout = proc.StandardOutput.ReadToEnd().Trim();
                Assert.AreNotSame("", stdout, "Couldn't find the location of msbuild.exe");
                msBuildPath = stdout;
            }

            using (var proc = new Process
            {
                StartInfo = new ProcessStartInfo
                {
                    FileName = msBuildPath,
                    WorkingDirectory = outDir,
                    UseShellExecute = false,
                    RedirectStandardOutput = true,
                    RedirectStandardInput = true,
                    CreateNoWindow = true,
                    Arguments = $"{cProject}.vcxproj /p:configuration={cConfig}"
                }
            })
            {
                proc.Start();

                var o = proc.StandardOutput.ReadToEnd();
                var worked = proc.ExitCode == 0;
                if (!worked)
                    Console.WriteLine(o);

                Assert.IsTrue(worked, "error while compiling C project");
            }
        }

        private void StartSBTWithArg(string outDir, string arg, string check, bool printOutput)
        {
            Console.WriteLine("StartSBTWithArg Files: " + string.Join(",", Directory.GetFiles(outDir)) + " / " + string.Join(",", Directory.GetDirectories(outDir)));
            Console.WriteLine("Windows? " + RuntimeInformation.IsOSPlatform(OSPlatform.Windows));
            using var proc = new Process();
            proc.StartInfo = new ProcessStartInfo
            {
                FileName = RuntimeInformation.IsOSPlatform(OSPlatform.Windows) ? "cmd.exe" : "bash",
                Arguments = RuntimeInformation.IsOSPlatform(OSPlatform.Windows) ? $"/C {arg}" : $"-c \"{arg}\"",
                WorkingDirectory = outDir,
                UseShellExecute = false,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                RedirectStandardInput = false,
                CreateNoWindow = false,
            };
            proc.Start();
            var outp = proc.StandardOutput.ReadToEnd();
            Console.WriteLine("OUTPUT " + outp);
            var outputList = outp.Split("\n").ToList();
            var worked = outputList.FindLastIndex(x => x.Contains(check)) > outputList.Count - 5;

            if (!worked)
            {
                Console.WriteLine("Scala test cases failed. Stdout:");
                Console.WriteLine(outp);
                Console.WriteLine("Stderr:");
                Console.WriteLine(proc.StandardError.ReadToEnd());
            }
            else if (printOutput) // print sbt output
            {
                Console.WriteLine(outp);
            }

            Assert.IsTrue(worked, "Scala test cases failed");
        }

    }
}
