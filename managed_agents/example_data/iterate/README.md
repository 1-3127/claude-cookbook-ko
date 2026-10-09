# Iterate, 테스트 통과시키기

의도적으로 버그 세 개를 넣은 `calc.py`와 이를 잡는 assertion 세 개가 있는 `test_calc.py`입니다. `CMA_iterate_fix_failing_tests.py`에서 사용합니다.

흥미로운 버그는 `test_mean`입니다. `mean()`이 내부에서 `add`와 `divide`를 호출하므로 다른 두 개를 수정하면 저절로 통과합니다. `mean()`을 직접 편집하는 agent는 과도하게 수정하는 것입니다.

