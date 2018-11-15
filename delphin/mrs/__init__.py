# -*- coding: utf-8 -*-

"""
This module contains classes and methods related to Minimal Recursion
Semantics [MRS]_.

.. [MRS] Copestake, Ann, Dan Flickinger, Carl Pollard,
  and Ivan A. Sag. "Minimal recursion semantics: An introduction."
  Research on language and computation 3, no. 2-3 (2005): 281-332.
.. [RMRS] Copestake, Ann. "Report on the design of RMRS."
  DeepThought project deliverable (2003).
.. [EDS] Stephan Oepen, Dan Flickinger, Kristina Toutanova, and
  Christopher D Manning. Lingo Redwoods. Research on Language and
  Computation, 2(4):575–596, 2004.;

  Stephan Oepen and Jan Tore Lønning. Discriminant-based MRS
  banking. In Proceedings of the 5th International Conference on
  Language Resources and Evaluation, pages 1250–1255, 2006.
.. [DMRS] Copestake, Ann. Slacker Semantics: Why superficiality,
  dependency and avoidance of commitment can be the right way to go.
  In Proceedings of the 12th Conference of the European Chapter of
  the Association for Computational Linguistics, pages 1–9.
  Association for Computational Linguistics, 2009.
"""

from ._mrs import (
    EP,
    HCons,
    ICons,
    MRS,
    var_split,
    var_sort,
    var_id)

