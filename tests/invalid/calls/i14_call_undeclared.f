program callundecl
  integer x
  x = 5
  call ghost(x)
  print *, x
end
