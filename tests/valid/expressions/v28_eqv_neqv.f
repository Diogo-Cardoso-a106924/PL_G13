program eqvtest
  logical a, b, c, d
  a = .TRUE.
  b = .TRUE.
  c = a .EQV. b
  d = a .NEQV. b
  print *, c
  print *, d
end
