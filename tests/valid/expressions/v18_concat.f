program concat
  character*10 a, b, c, d
  a = 'Hello'
  b = 'World'
  d = 'Again'
  c = a // b // d
  print *, c
end
