from pydantic import BaseModel


class Parent(BaseModel):
    a: int


class Child(Parent):
    b: int
    xs: list[str]


child = Child(a=1, b=2, xs=["a", "b"])
print(child.model_dump_json(indent=2))
print(Parent.model_dump_json(child, indent=2))
print(Child.model_dump_json(child, indent=2, exclude={"b"}))


print(Parent.model_validate(child))
print(type(Parent.model_validate(child)))
print(Parent(**child.model_dump()))


print(type(child).model_fields["xs"].annotation == list[str])
