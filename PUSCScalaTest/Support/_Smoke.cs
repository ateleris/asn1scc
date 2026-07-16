namespace PUS_C_Scala_Test;

[TestClass]
public class _Smoke
{
    [TestMethod]
    public void Python_S1_UPER_builds_and_passes()
    {
        var r = BuildCache.EnsureBuilt(new BuildKey(PUS_C_Service.S1, Lang.Python, Enc.UPER));
        Assert.IsTrue(r.TestsPassed, "Python S1 UPER enc/dec should pass");
        Assert.IsTrue(Directory.GetFiles(r.DatDir, "*.dat").Length > 0, "expected .dat artifacts");
    }

    [TestMethod]
    public void C_vs_Python_S1_UPER_interop()
    {
        var c = BuildCache.EnsureBuilt(new BuildKey(PUS_C_Service.S1, Lang.C, Enc.UPER));
        Assert.IsTrue(c.TestsPassed, "C S1 UPER enc/dec should pass");
        var py = BuildCache.EnsureBuilt(new BuildKey(PUS_C_Service.S1, Lang.Python, Enc.UPER));
        BuildCache.CompareDat(c, py, BuildCache.Exclusions(Lang.Python, PUS_C_Service.S1));
    }
}
