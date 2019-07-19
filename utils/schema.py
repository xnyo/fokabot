from schema import And, Use

StrippedString = And(str, Use(lambda x: x.strip()))
NonEmptyString: And = And(StrippedString, lambda x: bool(x))
