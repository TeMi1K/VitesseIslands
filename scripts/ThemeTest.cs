// ThemeTest.cs — syntax highlighting check for Vitesse Islands.
// Drop it into any .NET 8+ project next to Program.cs. It has no Main, so it won't clash
// with top-level statements, and there's no need to run it.
//
// Legend (what you should see):
//   keywords            int, public, var, null, new  -> rose, bold
//   control flow        if, for, return, switch      -> green, bold
//   classes / records   Player, Console, Math        -> cyan, italic
//   structs / enums     Point, Money, Rank           -> teal, italic
//   interfaces etc.     IScorable, ScoreChanged, TItem -> blue (italic)
//   methods             WriteLine, GetRank, Shout    -> olive, italic
//   properties          Score, Name, Length          -> gold, italic
//   constants / enum    MaxScore, Gold, Bonus        -> orchid
//   locals / fields     total, _history              -> sand (reassigned = faint underline)
//   parameters          points, text                 -> light text
//   namespaces          System.Linq, ThemeTest       -> lavender
//   strings / numbers   "Alice" / 120                -> clay / sea green
// TODO: this line should be yellow bold-italic

#nullable enable
#define VITESSE

using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using System.Text.RegularExpressions;
using System.Threading.Tasks;

namespace ThemeTest;

/// <summary>
/// Doc comment: tags like <see cref="Player"/> and <c>code</c> get their own colors.
/// </summary>
/// <param name="name">Player name.</param>
/// <param name="newScore">Score after the change.</param>
public delegate void ScoreChanged(string name, int newScore);

public enum Rank { Bronze, Silver, Gold }

[Flags]
public enum Perks : byte
{
    None = 0,
    Speed = 1 << 0,
    Luck = 1 << 1,
    All = Speed | Luck,
}

public interface IScorable
{
    int Score { get; }
    Rank GetRank();
}

public readonly struct Point(int x, int y)
{
    public int X { get; } = x;
    public int Y { get; } = y;

    public static Point operator +(Point a, Point b) => new(a.X + b.X, a.Y + b.Y);

    public override string ToString() => $"({X}, {Y})";
}

public readonly record struct Money(decimal Amount, string Currency = "EUR");

public record Player(string Name, int Score) : IScorable
{
    public const int MaxScore = 9_999;
    private static int _created;
    private readonly List<int> _history = [];

    public event ScoreChanged? OnScoreChanged;

    public Perks Perks { get; init; } = Perks.None;

    public Rank GetRank() => Score switch
    {
        >= 100 => Rank.Gold,
        >= 50 and < 100 => Rank.Silver,
        _ => Rank.Bronze,
    };

    public Player AddPoints(int points)
    {
        _created++;
        _history.Add(points);
        var updated = this with { Score = Math.Min(Score + points, MaxScore) };
        OnScoreChanged?.Invoke(Name, updated.Score);
        return updated;
    }
}

public sealed class Leaderboard<TItem> where TItem : IScorable
{
    private readonly Dictionary<string, TItem> _items = new();

    public int Count => _items.Count;

    public void Add(string key, TItem item) => _items[key] = item;

    public IEnumerable<TItem> Top(int count) =>
        _items.Values
            .Where(i => i.Score > 0)
            .OrderByDescending(i => i.Score)
            .Take(count);
}

public static class Extensions
{
    public static string Shout(this string text) => text.ToUpperInvariant() + "!";

    public static bool IsEven(this int value) => value % 2 == 0;

    [Obsolete("Use Shout instead")]
    public static string Yell(this string text) => text;
}

public static class Showcase
{
    private const double Bonus = 1.5;
    private static readonly Regex EmailRegex = new(@"^[\w.]+@\w+\.\w{2,}$", RegexOptions.Compiled);

    public static async Task<int> RunAsync(string[] args)
    {
        // Locals: plain vs. reassigned (reassigned ones get a faint underline)
        var board = new Leaderboard<Player>();
        int total = 0;
        string? nickname = args.Length > 0 ? args[0] : null;

        // Literals
        char letter = 'A';
        long big = 0xFF_FF_FFL;
        int mask = 0b1010_0101;
        float ratio = 3.14f;
        decimal price = 2.50m;
        bool ok = true;

        // Strings: escapes, verbatim, raw, interpolation with alignment/format
        string escaped = "Tab:\t| Newline:\n| Quote:\" | Unicode:\u00E9";
        string path = @"C:\RiderProjects\ConsoleApp3";
        string json = """
            { "name": "Alice", "score": 120 }
            """;
        string line = $"{nickname ?? "anon",-10} | {price:0.00} | {DateTime.Now:HH:mm}";
        string legacy = string.Format("{0} has {1} points", "Bob", 45);

        // Objects, events, lambdas
        Player alice = new("Alice", 120) { Perks = Perks.Speed | Perks.Luck };
        alice.OnScoreChanged += (name, score) => Console.WriteLine($"{name} -> {score}");
        alice = alice.AddPoints(10);

        board.Add(alice.Name, alice);
        board.Add("bob", new Player("Bob", 45));

        foreach (var p in board.Top(count: 3))
        {
            int boosted = (int)(p.Score * Bonus);
            total += boosted;
            Console.WriteLine($"{p.Name,-6} | {p.GetRank()} | {boosted} pts");
        }

        // Tuples and deconstruction
        (string Name, int Score) best = ("Eve", 73);
        var (bestName, bestScore) = best;
        Console.WriteLine($"{best.Name}: {bestScore} {bestName.Shout()}");

        // Pattern matching, operators, null handling
        object boxed = alice;
        if (boxed is Player { Score: > 100 } champion && !champion.Name.StartsWith('Z'))
        {
            Console.WriteLine(champion.Name);
        }

        if (nickname is not null && typeof(Player).Name == nameof(Player))
        {
            Console.WriteLine(nickname);
        }

        int length = nickname?.Length ?? 0;
        nickname ??= "guest";
        Point sum = new Point(1, 2) + new Point(3, 4);
        Money wallet = new(price * 4);

        // Local function, delegate, LINQ query syntax
        static int Square(int n) => n * n;
        Func<int, bool> isBig = n => n > 10;

        var squares =
            from n in Enumerable.Range(1, 10)
            where n.IsEven()
            select Square(n);

        // Control flow
        for (int i = 0; i < 3; i++)
        {
            if (i == 1) continue;
            if (isBig(i)) break;
        }

        while (total > 1_000)
        {
            total /= 2;
        }

        switch (alice.GetRank())
        {
            case Rank.Gold:
                Console.WriteLine("gold");
                break;
            default:
                goto case Rank.Gold;
        }

        try
        {
            checked { mask = int.MaxValue + mask; }
        }
        catch (OverflowException ex) when (ex.Message.Length > 0)
        {
            Debug.WriteLine(ex.Message);
        }
        finally
        {
            ok = !ok;
        }

        // Late-bound (dynamic) member: grey italic
        dynamic late = "dynamic";
        Console.WriteLine(late.Length);

#if VITESSE
        Console.WriteLine("active branch");
#else
        Console.WriteLine("inactive branch, should look faded");
#endif

        await Task.Delay(millisecondsDelay: 10);
        bool valid = EmailRegex.IsMatch("qm@example.lv");

        Console.WriteLine(string.Join(", ", squares));
        Console.WriteLine($"{letter} {big} {ratio} {escaped} {path} {json} {line} {legacy}");
        Console.WriteLine($"{length} {sum} {wallet} {valid} {ok} {board.Count}");
        return total;
    }
}
