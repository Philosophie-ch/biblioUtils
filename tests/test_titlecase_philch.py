from src.utils import titlecase_philch


def test_force_small() -> None:

    str_in = "Do The Evolutionary Origins Of Our Moral Beliefs Undermine Moral Knowledge?"

    desired = "Do the Evolutionary Origins of our Moral Beliefs Undermine Moral Knowledge?"

    output = titlecase_philch._force_small(str_in)

    assert output == desired


def test_preserve_already_capitalized() -> None:

    original_str = "Original"
    str_in = "original"

    output = titlecase_philch._preserve_already_capitalized(original_str, str_in)

    assert output == original_str

    original_str = "ThIs is A tEst"
    str_in = "this is a test"

    output = titlecase_philch._preserve_already_capitalized(original_str, str_in)

    assert output == original_str


def test_preserve_latex_commands() -> None:

    original_str = r"test \cited{bibkey}"
    str_in = r"test \Cited{bibkey}"

    desired = r"test \cited{bibkey}"

    output = titlecase_philch._preserve_latex_commands(original_str, str_in)

    assert output == desired


BENCHMARKS = {
    # <test_input>: <expected>
    r"Why was Darwin's view of Species rejected by Twentieth Century Biologists?": r"Why was Darwin's View of Species Rejected by Twentieth Century Biologists?",
    r"Ernst Mayr, the tree of life, and philosophy of biology": r"Ernst Mayr, the Tree of Life, and Philosophy of Biology",
    r"Eliminating the mystery from the concept of emergence": r"Eliminating the Mystery from the Concept of Emergence",
    r"Do the evolutionary origins of our moral beliefs undermine moral knowledge?": r"Do the Evolutionary Origins of our Moral Beliefs Undermine Moral Knowledge?",
    r"Against reduction": r"Against Reduction",
    r"New concepts can be learned": r"New Concepts Can Be Learned",
    r"The transmission sense of information": r"The Transmission Sense of Information",
    r"Response to commentaries on \citet{bergstrom-rosvall:2011} [\citet{godfreysmith_p:2011a},\citet{maclaurin_j:2011a} and \citet{shea_n:2011a}]": r"Response to Commentaries on \citet{bergstrom-rosvall:2011} [\citet{godfreysmith_p:2011a},\citet{maclaurin_j:2011a} and \citet{shea_n:2011a}]",
    r"Senders, receivers, and genetic information: comments on \citet{bergstrom-rosvall:2011}": r"Senders, Receivers, and Genetic Information: Comments on \citet{bergstrom-rosvall:2011}",
    r"Commentary on \citet{bergstrom-rosvall:2011}": r"Commentary on \citet{bergstrom-rosvall:2011}",
    r"What's transmitted? Inherited information [on \citet{bergstrom-rosvall:2011}]": r"What's Transmitted? Inherited Information [on \citet{bergstrom-rosvall:2011}]",
    r"Causation at different levels: tracking the commitments of mechanistic explanations": r"Causation at Different Levels: Tracking the Commitments of Mechanistic Explanations",
    r"The Complexity of approximating {MAP}s for Belief networks": r"The Complexity of Approximating {MAP}s for Belief Networks",
    r"The reasoning and lapses of James' \emph{The Will to Believe}": r"The Reasoning and Lapses of James' \emph{The Will to Believe}",
    r"Fire transfigured in T.S.~Eliot's \emph{Four Quartets}": r"Fire Transfigured in T.S.~Eliot's \emph{Four Quartets}",
    r"Faust.~The systematic study": r"Faust.~The Systematic Study",
    r"Reasonable.~A Treatise on legal justification": r"Reasonable.~A Treatise on Legal Justification",
    r"Comment on \citet{stinchcombe:1990}": r"Comment on \citet{stinchcombe:1990}",
    r"Some Notes on the notion of Naskh in the Kal{\=a}m": r"Some Notes on the Notion of Naskh in the Kal{\=a}m",
    r"\,`Present without being Present': Plotinus on Plato's Daim{\=o}n": r"\,`Present without Being Present': Plotinus on Plato's Daim{\=o}n",
    r"The Young Kierkegaard on/as Faust.~The systematic study and the Existential Identification.~A short presentation": r"The Young Kierkegaard on/as Faust.~The Systematic Study and the Existential Identification.~A Short Presentation",
    r"Plato on perception: A reply to \citet{turnbull_rg:1988}": r"Plato on Perception: A Reply to \citet{turnbull_rg:1988}",
    r"Group privilege and political division: The Problem of Fox Hunting in the UK": r"Group Privilege and Political Division: The Problem of Fox Hunting in the UK",
    r"\emph{Er{\=o}s Tyrannos} -- Philosophical passion and psychic ordering in the \emph{Republic}": r"\emph{Er{\=o}s Tyrannos} -- Philosophical Passion and Psychic Ordering in the \emph{Republic}",
    r"A Complete proof system for a dynamic Epistemic logic based Upon Finite $\Pi$-Calculus Processes": r"A Complete Proof System for a Dynamic Epistemic Logic Based Upon Finite $\Pi$-Calculus Processes",
    r"Truth Is (still) the norm for assertion: a reply to Littlejohn": r"Truth Is (Still) the Norm for Assertion: A Reply to Littlejohn",
    r"Reason, will and belief: insights From Duns Scotus and C.S.~Peirce": r"Reason, Will and Belief: Insights From Duns Scotus and C.S.~Peirce",
    r"Value-acquiring (\emph{Wertnehmung}) and meaning-bestowal (\emph{Sinnzueignung})": r"Value-Acquiring (\emph{Wertnehmung}) and Meaning-Bestowal (\emph{Sinnzueignung})",
    r"How can my mind move my limbs? Mental causation from Descartes to contemporary physicalism": r"How Can My Mind Move My Limbs? Mental Causation from Descartes to Contemporary Physicalism",
}


def test_dummy_titles() -> None:

    raw_titles = ["tiTle One", "TiTle tWo", "Title Three"]
    clean_titles = ["TiTle One", "TiTle TWo", "Title Three"]

    output_generator = titlecase_philch.main(raw_titles)
    output = list(output_generator)

    assert output == clean_titles


def test_ad_hoc_single_benchmark() -> None:

    i = 3
    title = list(BENCHMARKS.keys())[i]
    expected = list(BENCHMARKS.values())[i]

    output = titlecase_philch.titlecase_philch(title)

    assert output == expected


def test_benchmarks() -> None:

    output = list(titlecase_philch.main(list(BENCHMARKS.keys())))

    errors = [
        (i, expected, actual)
        for i, (expected, actual) in enumerate(zip(list(BENCHMARKS.values()), output))
        if expected != actual
    ]

    assert not errors, f"{len(errors)} errors found: {errors}"
